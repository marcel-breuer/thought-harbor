"""Application services for system-level operations."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """The current availability state of the application process."""

    status: str


class SystemService:
    """Expose system operations to delivery adapters."""

    def health(self) -> HealthStatus:
        """Return the process health state."""

        return HealthStatus(status="ok")
