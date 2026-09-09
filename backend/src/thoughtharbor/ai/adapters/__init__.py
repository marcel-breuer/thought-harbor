"""HTTP adapters for supported AI providers."""

from thoughtharbor.ai.adapters.ollama import OllamaProvider
from thoughtharbor.ai.adapters.openai_compatible import OpenAICompatibleProvider

__all__ = ["OllamaProvider", "OpenAICompatibleProvider"]
