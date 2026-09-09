"""Errors exposed by the provider-independent AI runtime."""


class AIError(Exception):
    """Base class for expected AI runtime failures."""


class ProviderConfigurationError(AIError):
    """Raised when a provider cannot be constructed from its configuration."""


class ProviderError(AIError):
    """A provider request failed with an actionable, provider-neutral error."""

    def __init__(self, provider: str, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.provider = provider
        self.code = code
        self.retryable = retryable


class CapabilityNotSupportedError(ProviderError):
    """Raised when a configured provider does not implement a capability."""

    def __init__(self, provider: str, capability: str) -> None:
        super().__init__(
            provider,
            "capability_not_supported",
            f"Provider {provider!r} does not support capability {capability!r}",
        )


class ContextWindowExceededError(AIError):
    """The request cannot fit within the configured model context window."""


class StructuredOutputError(AIError):
    """The provider returned no valid instance of the requested Pydantic schema."""
