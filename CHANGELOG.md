# Changelog

## v0.4.0 — 2026-05-24

> Project renamed: SourcePilot AI → **SourceHero AI**.

### Breaking changes

- **Cross-platform support** — Works on Windows and macOS from the same codebase
  - Added `Install-SourceHero.command` / `Start-SourceHero.command` (macOS, double-click)
  - Added `scripts/setup-macos.sh` / `scripts/start-macos.sh`
  - Electron main process now resolves Python across platforms (`python3.11` / `python3` / Homebrew paths)
- **Zero-dependency packaged build** — Uses [python-build-standalone](https://github.com/astral-sh/python-build-standalone) so end users don't need Python preinstalled
  - `scripts/build-runtime.sh` / `scripts/build-runtime.ps1` to fetch & populate the runtime for release
  - `desktop/electron-builder.yml` produces `.dmg` and NSIS installers
- **Platform data directory** — No more `./data/`. Uses each OS's standard location:
  - macOS: `~/Library/Application Support/SourceHero/`
  - Windows: `%APPDATA%\SourceHero\`
  - Linux: `~/.local/share/SourceHero/`
  - Override via `SOURCEHERO_DATA_DIR`
  - Legacy `./data/sourcepilot.db` auto-migrates on first launch
- **Environment variables renamed** — `SOURCEPILOT_*` → `SOURCEHERO_*` (`*_API_PORT`, `*_DASHBOARD_PORT`, `*_DATABASE_URL`, etc.)
- **Package / identifier renames** — pyproject `sourcepilot-ai` → `sourcehero-ai`; Electron `productName` → `SourceHero`

### New features

- **In-app API key configuration** — new *Settings* tab lets users paste their OpenAI key, choose a model, and test the connection without touching `.env`. Stored at `~/Library/Application Support/SourceHero/user_config.json`
- New endpoints: `GET/POST /settings`, `POST /settings/test-openai`

### UX

- First-launch welcome wizard (Try demo / Add my source / Skip)
- Persistent sidebar with live stats, data directory, and OpenAI key status
- Friendly error messages for network / parsing failures (403/404/timeout/DNS/encrypted PDF)
- Electron splash screen during backend warm-up
- Native menu bar: *File → Open Data Folder*, *Help → GitHub / Report Issue*
- Failure dialog now shows the log path and data directory instead of crashing silently

### Internals

- `app/config.py` rewritten on top of `platformdirs`; all data paths are now `@property` on `Settings`
- `app/services/user_settings.py` — JSON config persistence with env-var override
- `/health` returns `openai_configured`, `openai_key_preview`, `openai_key_source`, `openai_model`, `data_dir`
- `pyproject.toml` adds `platformdirs>=4.2.0`
- Version bumped 0.3.0 → 0.4.0

### Deferred to v0.5

- Local vector index (FAISS / Chroma) + semantic search
- macOS notarization / Windows code signing
- Scheduled ingestion and briefings
