"""Persist user-configurable settings (API keys, model choice) to the data dir.

This sits OUTSIDE the repo and OUTSIDE .env so the desktop app can write to it
without touching project files. Env vars still take precedence when set.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from app.config import data_dir_is_fallback, settings
from app.openai_models import DEFAULT_TEXT_MODEL

CONFIG_FILENAME = "user_config.json"
DEFAULT_MODEL = DEFAULT_TEXT_MODEL


def _config_path() -> Path:
    return settings.data_dir / CONFIG_FILENAME


def load_user_config() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_user_config(values: dict[str, Any]) -> dict[str, Any]:
    current = load_user_config()
    current.update({k: v for k, v in values.items() if v is not None})
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(current, indent=2), encoding="utf-8")
    return current


def clear_openai_key() -> None:
    current = load_user_config()
    current.pop("openai_api_key", None)
    _config_path().write_text(json.dumps(current, indent=2), encoding="utf-8")


def effective_openai_key() -> str | None:
    """Env var beats stored config (so a developer .env still works)."""
    return os.getenv("OPENAI_API_KEY") or load_user_config().get("openai_api_key")


def effective_openai_model() -> str:
    return os.getenv("OPENAI_MODEL") or load_user_config().get("openai_model") or DEFAULT_MODEL


def public_settings() -> dict[str, Any]:
    """What we expose to the dashboard — never leak the raw key."""
    key = effective_openai_key()
    return {
        "openai_configured": bool(key),
        "openai_key_preview": (key[:4] + "…" + key[-4:]) if key and len(key) > 12 else None,
        "openai_key_source": "env" if os.getenv("OPENAI_API_KEY") else ("config" if key else None),
        "openai_model": effective_openai_model(),
        "data_dir": str(settings.data_dir),
        "data_dir_fallback": data_dir_is_fallback(),
    }
