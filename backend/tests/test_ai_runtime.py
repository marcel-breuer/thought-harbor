"""Deterministic tests for provider adapters and shared AI request policy."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
import pytest
from pydantic import BaseModel

from thoughtharbor.ai.adapters.anthropic import AnthropicProvider
from thoughtharbor.ai.adapters.gemini import GeminiProvider
from thoughtharbor.ai.adapters.ollama import OllamaProvider
from thoughtharbor.ai.adapters.openai_compatible import OpenAICompatibleProvider
from thoughtharbor.ai.errors import ContextWindowExceededError, StructuredOutputError
from thoughtharbor.ai.models import ChatMessage, ChatRequest, EmbeddingRequest, ExtractionRequest
from thoughtharbor.ai.runtime import AIRuntime
from thoughtharbor.ai.settings import AISettings, CapabilitySettings


class ExtractedAnswer(BaseModel):
    answer: str


def provider_settings(**overrides: Any) -> CapabilitySettings:
    values: dict[str, Any] = {
        "provider": "ollama",
        "model": "test-model",
        "base_url": "http://testserver",
        "api_key": None,
        "timeout_seconds": 1,
        "max_retries": 0,
        "retry_delay_seconds": 0,
        "context_window": None,
        "max_output_tokens": None,
        "structured_retries": 1,
        "model_version": "test-version",
    }
    values.update(overrides)
    return CapabilitySettings(**values)


def transport_for(
    handler: Callable[[httpx.Request], httpx.Response | Awaitable[httpx.Response]],
) -> httpx.MockTransport:
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_ollama_chat_returns_safe_generation_metadata() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.content)
        assert payload["stream"] is False
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(
            200,
            json={"model": "test-model", "message": {"role": "assistant", "content": "hi"}},
        )

    provider = OllamaProvider(provider_settings(), transport=transport_for(handler))
    result = await provider.chat(ChatRequest((ChatMessage("user", "hello"),)))

    assert result.text == "hi"
    assert result.metadata.provider == "ollama"
    assert result.metadata.model_version == "test-version"
    assert "api_key" not in result.metadata.as_dict()
    assert len(result.metadata.configuration_fingerprint) == 64


@pytest.mark.asyncio
async def test_ollama_structured_output_is_validated_and_retried() -> None:
    responses = iter(
        [
            {"message": {"content": '{"answer": 42}'}},
            {"message": {"content": '{"answer": "accepted"}'}},
        ]
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["format"]["type"] == "object"
        return httpx.Response(200, json=next(responses))

    provider = OllamaProvider(provider_settings(), transport=transport_for(handler))
    result = await provider.extract(
        ExtractionRequest((ChatMessage("user", "extract"),)), ExtractedAnswer
    )

    assert result.value.answer == "accepted"


@pytest.mark.asyncio
async def test_qwen_embedding_uses_the_persisted_vector_dimension() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["model"] == "qwen3-embedding:0.6b"
        assert payload["dimensions"] == 768
        return httpx.Response(200, json={"embeddings": [[0.0] * 768]})

    provider = OllamaProvider(
        provider_settings(model="qwen3-embedding:0.6b"), transport=transport_for(handler)
    )
    result = await provider.embed(EmbeddingRequest(("hello",)))

    assert len(result.vectors[0]) == 768


@pytest.mark.asyncio
async def test_invalid_structured_output_never_becomes_a_result() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"message": {"content": "not-json"}})

    provider = OllamaProvider(
        provider_settings(structured_retries=1), transport=transport_for(handler)
    )

    with pytest.raises(StructuredOutputError):
        await provider.extract(
            ExtractionRequest((ChatMessage("user", "extract"),)), ExtractedAnswer
        )


@pytest.mark.asyncio
async def test_openai_compatible_adapter_sends_server_side_key_and_sorts_embeddings() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer secret"
        assert request.url.path == "/v1/embeddings"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": 1, "embedding": [2, 3]},
                    {"index": 0, "embedding": [0, 1]},
                ]
            },
        )

    settings = provider_settings(
        provider="openai_compatible", base_url="http://testserver/v1", api_key="secret"
    )
    provider = OpenAICompatibleProvider(settings, transport=transport_for(handler))
    result = await provider.embed(EmbeddingRequest(("first", "second")))

    assert result.vectors == ((0.0, 1.0), (2.0, 3.0))
    assert result.metadata.provider == "openai_compatible"
    assert "secret" not in result.metadata.configuration_fingerprint


@pytest.mark.asyncio
async def test_anthropic_adapter_maps_system_messages_and_uses_server_side_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        payload = json.loads(request.content)
        assert payload["system"] == "Be concise"
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        return httpx.Response(200, json={"content": [{"type": "text", "text": "hi"}]})

    provider = AnthropicProvider(
        provider_settings(provider="anthropic", base_url="http://testserver", api_key="secret"),
        transport=transport_for(handler),
    )
    result = await provider.chat(
        ChatRequest((ChatMessage("system", "Be concise"), ChatMessage("user", "hello")))
    )

    assert result.text == "hi"
    assert result.metadata.provider == "anthropic"
    assert "secret" not in result.metadata.configuration_fingerprint


@pytest.mark.asyncio
async def test_gemini_adapter_maps_assistant_role_and_structured_output() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/models/gemini-test:generateContent"
        assert request.headers["x-goog-api-key"] == "secret"
        payload = json.loads(request.content)
        assert payload["contents"][1]["role"] == "model"
        assert payload["generationConfig"]["responseMimeType"] == "application/json"
        assert payload["generationConfig"]["responseSchema"]["type"] == "object"
        return httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"answer":"accepted"}'}]}}]},
        )

    provider = GeminiProvider(
        provider_settings(
            provider="gemini",
            model="gemini-test",
            base_url="http://testserver/v1beta",
            api_key="secret",
        ),
        transport=transport_for(handler),
    )
    result = await provider.extract(
        ExtractionRequest((ChatMessage("user", "extract"), ChatMessage("assistant", "previous"))),
        ExtractedAnswer,
    )

    assert result.value.answer == "accepted"
    assert result.metadata.provider == "gemini"


@pytest.mark.asyncio
async def test_transient_provider_failure_is_retried() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"message": {"content": "recovered"}})

    provider = OllamaProvider(provider_settings(max_retries=1), transport=transport_for(handler))
    result = await provider.chat(ChatRequest((ChatMessage("user", "retry"),)))

    assert result.text == "recovered"
    assert calls == 2


@pytest.mark.asyncio
async def test_runtime_routes_capabilities_independently_and_enforces_context() -> None:
    settings = provider_settings(context_window=2)
    runtime = AIRuntime(
        OllamaProvider(settings, transport=transport_for(_chat_response)),
        OllamaProvider(settings, transport=transport_for(_chat_response)),
        OllamaProvider(settings, transport=transport_for(_chat_response)),
    )

    with pytest.raises(ContextWindowExceededError):
        await runtime.chat(ChatRequest((ChatMessage("user", "a message longer than two tokens"),)))


async def _chat_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={"message": {"content": "ok"}})


def test_environment_defaults_keep_all_capabilities_local(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "AI_DEFAULT_PROVIDER",
        "AI_CHAT_PROVIDER",
        "AI_EXTRACTION_PROVIDER",
        "AI_EMBEDDINGS_PROVIDER",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = AISettings.from_environment()

    assert settings.chat.provider == "ollama"
    assert settings.extraction.provider == "ollama"
    assert settings.embeddings.provider == "ollama"
    assert settings.chat.model == "qwen3.8"
    assert settings.extraction.model == "qwen3.8"
    assert settings.embeddings.model == "qwen3-embedding:0.6b"


def test_environment_defaults_include_native_external_provider_endpoints(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AI_CHAT_PROVIDER", "openai")
    monkeypatch.setenv("AI_CHAT_API_KEY", "secret")
    monkeypatch.setenv("AI_EXTRACTION_PROVIDER", "anthropic")
    monkeypatch.setenv("AI_EXTRACTION_API_KEY", "secret")
    monkeypatch.setenv("AI_EMBEDDINGS_PROVIDER", "gemini")
    monkeypatch.setenv("AI_EMBEDDINGS_API_KEY", "secret")

    settings = AISettings.from_environment()

    assert settings.chat.base_url == "https://api.openai.com/v1"
    assert settings.extraction.base_url == "https://api.anthropic.com"
    assert settings.embeddings.base_url == "https://generativelanguage.googleapis.com/v1beta"
