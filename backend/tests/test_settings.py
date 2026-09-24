from thoughtharbor.domain.settings import RuntimeSettingsService


def test_runtime_settings_snapshot_excludes_provider_secrets(monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-leak")
    monkeypatch.setenv("OPENROUTER_DEFAULT_MODEL", "safe-model")

    settings = RuntimeSettingsService().get()

    assert settings.chat_provider == "openrouter"
    assert settings.chat_model == "safe-model"
    assert settings.external_provider_enabled is True
    assert not hasattr(settings, "api_key")
