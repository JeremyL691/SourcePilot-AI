"""v0.4 cross-platform data dir wiring."""
from __future__ import annotations

import importlib
import os
from pathlib import Path


def test_data_dir_override(monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCEHERO_DATA_DIR", str(tmp_path))
    import app.config as config_module

    importlib.reload(config_module)
    s = config_module.Settings()
    s.ensure_dirs()

    assert s.data_dir == tmp_path
    assert s.db_dir == tmp_path / "db"
    assert s.raw_dir == tmp_path / "raw"
    assert s.vector_dir == tmp_path / "vector_index"
    assert s.logs_dir == tmp_path / "logs"
    assert s.database_url.endswith("/db/sourcehero.db")
    for sub in ("db", "raw", "vector_index", "logs", "processed"):
        assert (tmp_path / sub).is_dir()


def test_legacy_db_migration(monkeypatch, tmp_path, capsys):
    legacy_data = Path("./data")
    legacy_data.mkdir(exist_ok=True)
    legacy_db = legacy_data / "sourcepilot.db"
    legacy_db.write_bytes(b"sqlite_stub")
    try:
        monkeypatch.setenv("SOURCEHERO_DATA_DIR", str(tmp_path))
        import app.config as config_module

        importlib.reload(config_module)
        s = config_module.Settings()
        s.ensure_dirs()
        migrated = tmp_path / "db" / "sourcehero.db"
        assert migrated.is_file()
        assert migrated.read_bytes() == b"sqlite_stub"
    finally:
        if legacy_db.exists():
            legacy_db.unlink()


def test_settings_user_agent_v04():
    from app.config import settings

    assert "0.4" in settings.user_agent
    assert "SourceHero" in settings.user_agent
