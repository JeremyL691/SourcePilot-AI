from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("SOURCEPILOT_DATABASE_URL", "sqlite:///./data/sourcepilot.db")
    raw_dir: Path = Path(os.getenv("SOURCEPILOT_RAW_DIR", "./data/raw"))
    vector_dir: Path = Path(os.getenv("SOURCEPILOT_VECTOR_DIR", "./data/vector_index"))
    http_timeout: int = int(os.getenv("SOURCEPILOT_HTTP_TIMEOUT", "20"))
    api_port: int = int(os.getenv("SOURCEPILOT_API_PORT", "8000"))
    dashboard_port: int = int(os.getenv("SOURCEPILOT_DASHBOARD_PORT", "8501"))
    user_agent: str = "SourcePilotAI/0.3 (+local-first data intelligence)"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY") or None
    openai_model: str | None = os.getenv("OPENAI_MODEL") or None

    def ensure_dirs(self) -> None:
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        Path("./data/processed").mkdir(parents=True, exist_ok=True)


settings = Settings()
