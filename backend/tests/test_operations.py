import json
import logging

from thoughtharbor.operations.health import DependencyStatus, HealthService
from thoughtharbor.operations.logging import JsonFormatter
from thoughtharbor.operations.metrics import Metrics


def test_readiness_aggregates_dependency_failures(monkeypatch) -> None:
    checks = (
        DependencyStatus("postgresql", "ok", "reachable"),
        DependencyStatus("redis", "unavailable", "queue is unreachable"),
    )
    monkeypatch.setattr(HealthService, "_database", staticmethod(lambda: checks[0]))
    monkeypatch.setattr(HealthService, "_redis", staticmethod(lambda: checks[1]))
    monkeypatch.setattr(HealthService, "_storage", staticmethod(lambda: checks[0]))
    monkeypatch.setattr(HealthService, "_ai_providers", staticmethod(lambda: checks[0]))
    monkeypatch.setattr(HealthService, "_worker", staticmethod(lambda: checks[0]))

    status, actual_checks = HealthService().readiness()

    assert status == "unavailable"
    assert actual_checks[1] == checks[1]


def test_metrics_render_method_and_status_class() -> None:
    metrics = Metrics()
    metrics.observe_request("GET", 200)
    metrics.observe_request("GET", 503)

    output = metrics.prometheus()

    assert 'method="GET",status_class="2"} 1' in output
    assert 'method="GET",status_class="5"} 1' in output


def test_json_logging_only_emits_safe_correlation_fields() -> None:
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "request completed", (), None)
    record.request_id = "request-123"
    record.document_text = "private document content"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "request-123"
    assert payload["message"] == "request completed"
    assert "document_text" not in payload
