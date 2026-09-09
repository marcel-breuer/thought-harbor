"""Small JSON logging setup for local diagnostics."""

import json
import logging
import os
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Serialize safe log fields while excluding arbitrary sensitive extras."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in ("request_id", "job_id", "status_code", "path", "method"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=True)


def configure_logging() -> None:
    """Install one configurable JSON stream handler per process."""

    root = logging.getLogger()
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
    if any(isinstance(handler.formatter, JsonFormatter) for handler in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
