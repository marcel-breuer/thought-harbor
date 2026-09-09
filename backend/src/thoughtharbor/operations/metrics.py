"""Optional in-process Prometheus-compatible request counters."""

from collections import Counter


class Metrics:
    """Keep lightweight counters without a mandatory metrics service."""

    def __init__(self) -> None:
        self.requests: Counter[tuple[str, str]] = Counter()

    def observe_request(self, method: str, status_code: int) -> None:
        """Count a request by method and response class."""

        self.requests[(method, str(status_code // 100))] += 1

    def prometheus(self) -> str:
        """Render counters in a format accepted by Prometheus scrapers."""

        lines = [
            "# HELP thoughtharbor_http_requests_total HTTP responses by method and class",
            "# TYPE thoughtharbor_http_requests_total counter",
        ]
        for (method, status_class), count in sorted(self.requests.items()):
            labels = f'method="{method}",status_class="{status_class}"'
            lines.append(f"thoughtharbor_http_requests_total{{{labels}}} {count}")
        return "\n".join(lines) + "\n"


metrics = Metrics()
