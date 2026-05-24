from __future__ import annotations

import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

try:
    from platformdirs import user_data_dir
except ImportError:  # pragma: no cover - dependency missing pre-install
    user_data_dir = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

APP_NAME = "SourceHero"
APP_AUTHOR = "SourceHero"


def _default_data_dir() -> Path:
    override = os.getenv("SOURCEHERO_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if user_data_dir is not None:
        return Path(user_data_dir(APP_NAME, APP_AUTHOR, roaming=True))
    return Path("./data").resolve()


def _migrate_legacy_data(target_root: Path) -> None:
    legacy_db = Path("./data/sourcepilot.db").resolve()
    new_db = target_root / "db" / "sourcehero.db"
    if legacy_db.exists() and not new_db.exists():
        new_db.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(legacy_db, new_db)
            logger.info("Migrated legacy DB %s -> %s", legacy_db, new_db)
        except OSError as exc:  # pragma: no cover
            logger.warning("Could not migrate legacy DB: %s", exc)


@dataclass(frozen=True)
class Settings:
    data_dir: Path = field(default_factory=_default_data_dir)
    http_timeout: int = int(os.getenv("SOURCEHERO_HTTP_TIMEOUT", "20"))
    api_port: int = int(os.getenv("SOURCEHERO_API_PORT", "8000"))
    dashboard_port: int = int(os.getenv("SOURCEHERO_DASHBOARD_PORT", "8501"))
    user_agent: str = "SourceHeroAI/0.4 (+local-first data intelligence)"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str | None = os.getenv("OPENAI_MODEL") or None

    @property
    def db_dir(self) -> Path:
        return self.data_dir / "db"

    @property
    def raw_dir(self) -> Path:
        override = os.getenv("SOURCEHERO_RAW_DIR")
        return Path(override).expanduser() if override else self.data_dir / "raw"

    @property
    def vector_dir(self) -> Path:
        override = os.getenv("SOURCEHERO_VECTOR_DIR")
        return Path(override).expanduser() if override else self.data_dir / "vector_index"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def database_url(self) -> str:
        override = os.getenv("SOURCEHERO_DATABASE_URL")
        if override:
            return override
        return f"sqlite:///{(self.db_dir / 'sourcehero.db').as_posix()}"

    def ensure_dirs(self) -> None:
        for directory in (self.data_dir, self.db_dir, self.raw_dir, self.vector_dir, self.logs_dir, self.processed_dir):
            directory.mkdir(parents=True, exist_ok=True)
        _migrate_legacy_data(self.data_dir)


settings = Settings()
settings.ensure_dirs()
