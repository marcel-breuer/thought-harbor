"""HTTP middleware shared by API delivery adapters."""

from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


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

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        await self.app(scope, receive, send_with_request_id)
