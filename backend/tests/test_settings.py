from thoughtharbor.domain.settings import RuntimeSettingsService


def test_runtime_settings_snapshot_excludes_provider_secrets(monkeypatch) -> None:
    monkeypatch.setenv("AI_CHAT_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_CHAT_MODEL", "safe-model")
    monkeypatch.setenv("AI_CHAT_API_KEY", "must-not-leak")

    settings = RuntimeSettingsService().get()

    assert settings.chat_provider == "openai_compatible"
    assert settings.chat_model == "safe-model"
    assert settings.external_provider_enabled is True
    assert not hasattr(settings, "api_key")
