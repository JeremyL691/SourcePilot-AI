"""v0.4.1 B3 — user_settings round-trips an unknown model name without erasing it."""
from __future__ import annotations

import importlib
import json

import app.services.user_settings as user_settings


def test_unknown_model_is_preserved(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCEHERO_DATA_DIR", str(tmp_path))
    import app.config as config_module
    importlib.reload(config_module)
    importlib.reload(user_settings)

    user_settings.save_user_config({"openai_model": "gpt-5-pro-custom-2099"})

    saved = json.loads((tmp_path / "user_config.json").read_text())
    assert saved["openai_model"] == "gpt-5-pro-custom-2099"

    assert user_settings.effective_openai_model() == "gpt-5-pro-custom-2099"


def test_env_override_beats_saved_key(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCEHERO_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env-123456789")
    import app.config as config_module
    importlib.reload(config_module)
    importlib.reload(user_settings)

    user_settings.save_user_config({"openai_api_key": "sk-stored-key-different"})
    assert user_settings.effective_openai_key() == "sk-from-env-123456789"
    pub = user_settings.public_settings()
    assert pub["openai_key_source"] == "env"


def test_clear_openai_key(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCEHERO_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    import app.config as config_module
    importlib.reload(config_module)
    importlib.reload(user_settings)

    user_settings.save_user_config({"openai_api_key": "sk-temp-123456789"})
    assert user_settings.effective_openai_key() == "sk-temp-123456789"

    user_settings.clear_openai_key()
    assert user_settings.effective_openai_key() is None
