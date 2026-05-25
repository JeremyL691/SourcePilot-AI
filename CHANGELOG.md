# Changelog

## v0.5.0 — 2026-05-25

Feature release focused on retrieval quality, recurring automation, and a
cleanup of the OpenAI model configuration UX.

### Added

- **Hybrid retrieval.** `POST /search` now accepts
  `retrieval_mode=lexical|hybrid|semantic`, and the response reports the
  `effective_retrieval_mode` actually used.
- **Persistent semantic index.** Chunk embeddings can now be stored locally
  under the app data directory, inspected via `GET /index/status`, and
  rebuilt with `POST /index/rebuild`.
- **Recurring schedules.** New `scheduled_jobs` / `scheduled_job_runs` tables
  and schedule APIs:
  `GET/POST/PATCH/DELETE /schedules` plus `POST /schedules/{id}/run-now`.
- **Scheduled briefings and auto-ingest.** The Streamlit app can now create
  daily/weekly recurring source ingestion and briefing jobs while the app is
  running.

### Changed

- **Official OpenAI model picker.** Settings now default to `gpt-5.4-mini`
  and list current real text-capable OpenAI model IDs instead of stale
  placeholder values. Custom saved model names are still preserved.
- **Briefings accept filters.** `BriefingRequest` now supports the same
  source, collection, and tag filters as search.
- **Health reporting includes index state.** `/health` now surfaces semantic
  index availability and chunk coverage in addition to the existing OpenAI
  status fields.

### Fixed

- **Semantic index rebuild is non-destructive on failure.** A rebuild now
  preserves the last good index unless the new pass completes successfully.
- **Index writes are atomic.** Local vector index updates now use a lock and
  atomic file replacement instead of racy read-modify-write cycles.
- **Schedules no longer self-disable on transient runtime failures.** Failed
  runs record `last_error` and advance `next_run_at`, but the recurring job
  remains active for the next interval unless the user pauses it.
- **Schedule creation validates source references.** Auto-ingest schedules now
  reject nonexistent `source_id` values up front instead of creating doomed
  jobs that only fail later.
- **Partial indexes are not advertised as ready.** Semantic mode only becomes
  ready once the stored embedding count covers the full chunk corpus.

### Tests

- Added coverage for hybrid fallback behavior, semantic index rebuild and
  failure recovery, vector cleanup on source deletion, schedules retry
  behavior, invalid schedule references, and the refreshed OpenAI model
  defaults. Suite now passes 49 tests.

---

## v0.4.1 — 2026-05-24

Quality pass after the v0.4 cross-platform release. No new features — just bug
fixes and UX polish surfaced by an internal audit before producing installers.

### Fixed

- **Paused sources are now actually paused.** `ingest_source` previously
  ignored the paused status entirely and would always overwrite it with
  `active` or `failed` on completion. It now refuses to ingest a paused
  source (returns HTTP 409 from `/sources/{id}/ingest`) and preserves the
  paused state even if a concurrent edit pauses the source mid-run.
- **Welcome wizard "Add my own source" button now goes somewhere.** It
  dismisses the welcome banner and surfaces a hint pointing at the Step 1
  add-source form. Previously it just reloaded the same view.
- **Settings model dropdown preserves custom model names.** If you saved an
  unrecognized model (e.g., `gpt-5-pro-experimental`), the dropdown used to
  silently reset to `gpt-4.1-mini` on reload. It now keeps your choice.
- **Pipeline error messages are sanitized.** Ingestion failures no longer
  leak full exception reprs / partial tracebacks into the UI; common cases
  (403, 404, timeout, DNS, TLS, encrypted PDFs) render as short readable
  English. Full exceptions still go to the logger.
- **Demo seed now also indexes.** New endpoint `POST /demo/seed-and-ingest`
  seeds the three demo sources AND runs ingestion for each in one call. The
  welcome page "Try the demo" button uses it so first-time users land on a
  knowledge base that actually has searchable content.
- **Graceful fallback when the data directory is read-only.** Locked-down
  corporate Macs / sandboxed CI environments where
  `~/Library/Application Support/` is unwritable used to crash the backend
  at import time. We now probe the directory and fall back to a per-user
  tempdir with a logged warning, exposing the fact via
  `/health → data_dir_fallback`.
- **`/settings/test-openai` returns specific errors.** Auth failures →
  "Invalid API key", rate limits → "Rate limited", missing model → "Model
  not available", etc. Replaces the previous catch-all "OpenAI call failed".

### Changed

- Sidebar hides the user's home directory: `~/Library/Application
  Support/SourceHero` instead of the full path. The full path is in the
  Settings tab.
- Sources table only shows the columns that matter (name, type, status,
  URL link, last indexed) with a human-readable timestamp.

### Tests

- 13 new test cases across paused-source behavior, error sanitization, the
  seed-and-index endpoint, settings round-trip with custom models, and
  read-only data dir fallback. Suite went from 21 to 34 passing tests.

---

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
