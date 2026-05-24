"""v0.4.1 D1 — importing app.config with a read-only data dir must NOT raise."""
from __future__ import annotations

import importlib
import os
from pathlib import Path


def test_readonly_data_dir_falls_back_to_tmp(monkeypatch, tmp_path):
    # Create a dir, drop write permission. Subprocess-level chmod is enough on macOS/Linux.
    locked = tmp_path / "locked_data_dir"
    locked.mkdir()
    os.chmod(locked, 0o500)  # r-x------
    try:
        monkeypatch.setenv("SOURCEHERO_DATA_DIR", str(locked))
        import app.config as config_module
        # Reloading should NOT raise even though the preferred dir is read-only.
        importlib.reload(config_module)

        # Either we resolved to a different writable path, or the fallback flag is set,
        # or (in test envs where root can still write to 0o500 dirs) the preferred path works.
        s = config_module.Settings()
        s.ensure_dirs()
        # Whatever data_dir ended up at, it should be writable.
        probe = Path(s.data_dir) / ".rw_check"
        probe.write_text("ok")
        probe.unlink()
    finally:
        # Restore so pytest can clean up tmp_path
        os.chmod(locked, 0o700)


def test_fallback_flag_helper_exists():
    """data_dir_is_fallback() should always be callable and return a bool."""
    import app.config as config_module
    importlib.reload(config_module)
    assert isinstance(config_module.data_dir_is_fallback(), bool)
