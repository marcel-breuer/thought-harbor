"""HTTP middleware shared by API delivery adapters."""

import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from uuid import uuid4

from fastapi import Request
from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.operations.metrics import metrics

logger = logging.getLogger(__name__)


class RequestRateLimiter:
    """Small process-local fixed-window limiter for expensive HTTP operations."""

    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, key: str, *, maximum: int, window_seconds: int) -> int | None:
        """Return remaining lockout seconds after consuming one request."""

        now = time.monotonic()
        with self._lock:
            requests = self._requests[key]
            while requests and now - requests[0] >= window_seconds:
                requests.popleft()
            if len(requests) >= maximum:
                return max(1, int(window_seconds - (now - requests[0])))
            requests.append(now)
            return None


request_rate_limiter = RequestRateLimiter()
_RATE_LIMITS = {
    "auth": (10, 300),
    "upload": (30, 300),
    "search": (60, 60),
    "ai": (20, 60),
}


def rate_limit_dependency(bucket: str) -> Callable[[Request], None]:
    """Build a FastAPI dependency for a named process-local request budget."""

    maximum, window_seconds = _RATE_LIMITS[bucket]

    def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        retry_after = request_rate_limiter.retry_after(
            f"{bucket}:{client}", maximum=maximum, window_seconds=window_seconds
        )
        if retry_after is not None:
            raise ApplicationError(
                "RATE_LIMITED",
                "Too many requests. Try again later.",
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

    return dependency


def _valid_request_id(value: str | None) -> str:
    """Keep safe caller-provided IDs and generate one for invalid input."""

    if value and len(value) <= 128 and value.isprintable():
        return value
    return str(uuid4())


class RequestIdMiddleware:
    """Attach a correlation ID to request state and every HTTP response."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _valid_request_id(Headers(scope=scope).get("x-request-id"))
        scope.setdefault("state", {})["request_id"] = request_id
        status_code = 500

        async def send_with_request_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)
        method = scope.get("method", "")
        path = scope.get("path", "")
        metrics.observe_request(method, status_code)
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": status_code,
            },
        )
