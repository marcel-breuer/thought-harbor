"""Deterministic tests for OpenRouter models and request contracts."""

import json

import httpx
import pytest
from pydantic import BaseModel

import thoughtharbor.ai.runtime as runtime_module
from thoughtharbor.ai.adapters.openai_compatible import OpenAICompatibleProvider
from thoughtharbor.ai.catalog import OpenRouterModelCatalog
from thoughtharbor.ai.errors import ProviderError
from thoughtharbor.ai.models import ChatMessage, ChatRequest, EmbeddingRequest, ExtractionRequest
from thoughtharbor.ai.runtime import AIRuntime
from thoughtharbor.ai.settings import AISettings, CapabilitySettings


class ExtractedAnswer(BaseModel):
    answer: str


def settings(**overrides: object) -> CapabilitySettings:
    values: dict[str, object] = {
        "provider": "openrouter",
        "model": "openai/gpt-4o-mini",
        "base_url": "https://openrouter.test/api/v1",
        "api_key": "server-secret",
        "timeout_seconds": 1,
        "max_retries": 0,
        "retry_delay_seconds": 0,
        "context_window": None,
        "max_output_tokens": None,
        "structured_retries": 0,
        "model_version": None,
    }
    values.update(overrides)
    return CapabilitySettings(**values)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_openrouter_chat_and_structured_output_use_the_selected_model() -> None:
    requested_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_paths.append(request.url.path)
        assert request.headers["authorization"] == "Bearer server-secret"
        payload = json.loads(request.content)
        assert payload["model"] == "anthropic/claude-test"
        if "response_format" in payload:
            return httpx.Response(
                200,
                json={
                    "model": "anthropic/claude-test:free",
                    "choices": [{"message": {"content": '{"answer":"valid"}'}}],
                },
            )
        return httpx.Response(
            200,
            json={
                "model": "anthropic/claude-test:free",
                "choices": [{"message": {"content": "hello"}}],
            },
        )

    provider = OpenAICompatibleProvider(
        settings(model="anthropic/claude-test"),
        provider_name="openrouter",
        transport=httpx.MockTransport(handler),
    )
    chat = await provider.chat(ChatRequest((ChatMessage("user", "hi"),)))
    extraction = await provider.extract(
        ExtractionRequest((ChatMessage("user", "extract"),)), ExtractedAnswer
    )

    assert requested_paths == ["/api/v1/chat/completions"] * 2
    assert chat.text == "hello"
    assert extraction.value.answer == "valid"
    assert chat.metadata.model == "anthropic/claude-test:free"
    assert extraction.metadata.model == "anthropic/claude-test:free"
    assert "server-secret" not in str(chat.metadata.as_dict())


@pytest.mark.asyncio
async def test_openrouter_embeddings_request_fixed_dimensions() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert request.url.path == "/api/v1/embeddings"
        assert payload["model"] == "openai/text-embedding-3-small"
        assert payload["dimensions"] == 768
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "data": [{"index": 0, "embedding": [0.0] * 768}],
            },
        )

    provider = OpenAICompatibleProvider(
        settings(model="openai/text-embedding-3-small"),
        provider_name="openrouter",
        transport=httpx.MockTransport(handler),
    )
    result = await provider.embed(EmbeddingRequest(("source text",)))

    assert len(result.vectors[0]) == 768
    assert result.metadata.provider == "openrouter"


@pytest.mark.asyncio
async def test_model_catalog_filters_to_json_schema_capable_text_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "catalog-secret")

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/models"
        assert request.url.params["output_modalities"] == "text"
        assert request.url.params["supported_parameters"] == "response_format"
        assert request.headers["authorization"] == "Bearer catalog-secret"
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "id": "openai/gpt-test",
                        "name": "GPT Test",
                        "context_length": 32000,
                        "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                        "supported_parameters": ["response_format"],
                    },
                    {
                        "id": "openai/chat-only",
                        "name": "Chat Only",
                        "supported_parameters": ["temperature"],
                    },
                ]
            },
        )

    models = await OpenRouterModelCatalog(httpx.MockTransport(handler)).generation_models()

    assert len(models) == 1
    assert models[0].id == "openai/gpt-test"
    assert models[0].context_length == 32000
    assert models[0].prompt_price == 0.000001


@pytest.mark.asyncio
async def test_openrouter_catalog_requires_server_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with pytest.raises(ProviderError, match="OPENROUTER_API_KEY"):
        await OpenRouterModelCatalog().generation_models()


def test_user_model_override_does_not_change_deployment_defaults() -> None:
    configured = AISettings(
        chat=settings(model="openai/default"),
        extraction=settings(model="openai/default"),
        embeddings=settings(model="openai/embedding"),
    )
    runtime = AIRuntime.from_settings(configured)
    selected = runtime.with_generation_model("anthropic/claude-user-choice")

    assert selected.chat_provider.settings.model == "anthropic/claude-user-choice"
    assert selected.extraction_provider.settings.model == "anthropic/claude-user-choice"
    assert selected.embedding_provider.settings.model == "openai/embedding"
    assert runtime.chat_provider.settings.model == "openai/default"


@pytest.mark.asyncio
async def test_removed_user_model_falls_back_to_deployment_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested_models: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        requested_models.append(payload["model"])
        if payload["model"] == "provider/retired-model":
            return httpx.Response(404, json={"error": {"message": "Model not found"}})
        return httpx.Response(
            200,
            json={
                "model": "provider/default-model",
                "choices": [{"message": {"content": "default answer"}}],
            },
        )

    transport = httpx.MockTransport(handler)

    def provider_for(capability_settings: CapabilitySettings) -> OpenAICompatibleProvider:
        return OpenAICompatibleProvider(
            capability_settings, provider_name="openrouter", transport=transport
        )

    monkeypatch.setattr(runtime_module, "_provider", provider_for)
    configured = AISettings(
        chat=settings(model="provider/default-model"),
        extraction=settings(model="provider/default-model"),
        embeddings=settings(model="provider/embedding"),
    )
    result = await AIRuntime.from_settings(configured).chat(
        ChatRequest((ChatMessage("user", "hello"),)), model_id="provider/retired-model"
    )

    assert requested_models == ["provider/retired-model", "provider/default-model"]
    assert result.text == "default answer"
    assert result.metadata.model == "provider/default-model"
