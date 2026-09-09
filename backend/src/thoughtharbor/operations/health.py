"""Dependency checks for liveness and readiness endpoints."""

import logging
import os
from dataclasses import dataclass
from typing import Literal

import httpx
import redis
from sqlalchemy import text

from thoughtharbor.ai.settings import AISettings
from thoughtharbor.db.session import engine
from thoughtharbor.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DependencyStatus:
    """Safe health result for one local dependency."""

    name: str
    status: Literal["ok", "unavailable"]
    detail: str


class HealthService:
    """Check local dependencies without exposing credentials or content."""

    def readiness(self) -> tuple[Literal["ok", "unavailable"], tuple[DependencyStatus, ...]]:
        """Return aggregate readiness and safe per-dependency statuses."""

        checks = (
            self._database(),
            self._redis(),
            self._storage(),
            self._ai_providers(),
            self._worker(),
        )
        status: Literal["ok", "unavailable"] = "ok"
        if not all(check.status == "ok" for check in checks):
            status = "unavailable"
        return status, checks

    @staticmethod
    def _database() -> DependencyStatus:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            logger.debug("database readiness check failed", exc_info=True)
            return DependencyStatus("postgresql", "unavailable", "database is unreachable")
        return DependencyStatus("postgresql", "ok", "reachable")

    @staticmethod
    def _redis() -> DependencyStatus:
        client = redis.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        try:
            client.ping()
        except Exception:
            logger.debug("redis readiness check failed", exc_info=True)
            return DependencyStatus("redis", "unavailable", "queue is unreachable")
        finally:
            client.close()
        return DependencyStatus("redis", "ok", "reachable")

    @staticmethod
    def _storage() -> DependencyStatus:
        root = os.environ.get("STORAGE_ROOT", ".data/files")
        try:
            os.makedirs(root, exist_ok=True)
            probe = os.path.join(root, ".readiness-probe")
            with open(probe, "w", encoding="utf-8") as handle:
                handle.write("ok")
            os.unlink(probe)
        except OSError:
            logger.debug("storage readiness check failed", exc_info=True)
            return DependencyStatus("storage", "unavailable", "local storage is not writable")
        return DependencyStatus("storage", "ok", "writable")

    @staticmethod
    def _ai_providers() -> DependencyStatus:
        settings = AISettings.from_environment()
        providers = {
            (capability.provider, capability.base_url)
            for capability in (settings.chat, settings.extraction, settings.embeddings)
        }
        if not providers or any(not url for _, url in providers):
            return DependencyStatus("ai", "unavailable", "provider URL is not configured")
        try:
            with httpx.Client(timeout=1) as client:
                for _, url in providers:
                    response = client.get(url)
                    if response.status_code >= 500:
                        raise RuntimeError("provider unavailable")
        except Exception:
            logger.debug("AI readiness check failed", exc_info=True)
            return DependencyStatus("ai", "unavailable", "configured provider is unreachable")
        return DependencyStatus("ai", "ok", "configured provider reachable")

    @staticmethod
    def _worker() -> DependencyStatus:
        try:
            responses = celery_app.control.inspect(timeout=1).ping() or {}
        except Exception:
            logger.debug("worker readiness check failed", exc_info=True)
            responses = {}
        if not responses:
            return DependencyStatus("celery", "unavailable", "no worker heartbeat")
        return DependencyStatus("celery", "ok", f"{len(responses)} worker(s) responding")
