# SourceHero AI

SourceHero AI is a local-first personal knowledge base for people who save a lot of links, PDFs, feeds, notes, and research conversations, then forget where the useful parts went.

I built it to answer a simple question: what if my reading pile could turn into a searchable, cited knowledge base on my own computer, without needing to set up a cloud database or a paid AI workflow first?

The app runs locally on Windows and macOS, stores data in SQLite, ingests webpages/RSS/PDFs, lets you organize sources with collections and tags, and answers questions using only the evidence it has indexed. If you have an OpenAI key, it can synthesize a nicer answer. If not, it still works fully offline with local extractive answers and citations.

> Previously released as **SourcePilot AI**. The project was renamed to SourceHero AI in v0.4.

## What It Does

- Save webpages, RSS feeds, PDFs, and conversation summaries into one local library.
- Ingest and clean source text automatically.
- Chunk and deduplicate documents before indexing.
- Search by keyword with filters for source type, source, collection, and tag.
- Ask grounded questions and get cited answers instead of unsupported guesses.
- Save each Ask conversation as a Markdown summary back into the knowledge base.
- Browse documents and inspect the exact chunks used for retrieval.
- Organize sources and documents with collections and tags.
- Run as a desktop app through Electron, with FastAPI and Streamlit started for you.
- Configure your OpenAI key inside the app — no editing dotfiles.
- Stay usable without an OpenAI API key.

## Current Status

This is an early but usable desktop version. The goal is not to be another generic chatbot. The goal is to become a practical personal knowledge workspace: collect information, keep it organized, ask questions later, and preserve useful conversations as reusable notes.

The current version includes:

- FastAPI backend
- SQLite/SQLAlchemy data model
- Streamlit dashboard with a first-run welcome wizard
- Electron desktop shell with a splash screen and native menu
- RSS, webpage, PDF, and saved conversation ingestion
- Local TF-IDF style retrieval
- Cited answers and briefings
- Collections and tags
- Demo source seeding
- In-app Settings tab for the OpenAI API key and model
- Cross-platform setup scripts (Windows PowerShell + macOS bash)
- Per-user data directory on each platform
- Friendly error messages for common ingestion failures
- Focused automated tests

## What's New In v0.4

- **Cross-platform.** First-class macOS support alongside Windows. Same code, same UI, separate setup scripts.
- **In-app API key.** A new Settings tab lets you paste your OpenAI key, pick a model, and test the connection without touching `.env`. The key is stored in your local data directory.
- **First-run wizard.** When the knowledge base is empty, the app shows a welcome screen with one click to load demo sources, add your own, or skip.
- **Per-user data directory.** Data now lives in the standard platform location instead of inside the project folder, so updating the source code never wipes your library. An old `./data/sourcepilot.db` is migrated automatically.
- **Rename.** SourcePilot → SourceHero across identifiers, environment variables (`SOURCEHERO_*`), database filename, and packaging metadata.
- **Better error messages.** Network and parsing failures show readable English instead of stack traces.

See [CHANGELOG.md](CHANGELOG.md) for the full list.

## Quick Start On macOS

Install the two system dependencies first:

- Python 3.11 or newer  
  The easiest way is Homebrew: `brew install python@3.11`.

- Node.js LTS  
  Either `brew install node` or the installer from <https://nodejs.org/>.

Then clone the project and double-click:

```text
Install-SourceHero.command
```

After setup finishes, start the app with:

```text
Start-SourceHero.command
```

If macOS Gatekeeper blocks the first launch, right-click the file and choose **Open**.

## Quick Start On Windows

Install the two system dependencies first:

- Python 3.11 or newer  
  When installing Python, check `Add python.exe to PATH`.

- Node.js LTS  
  The default installer options are fine.

Then clone or open the project folder and double-click:

```text
Install-SourceHero.bat
```

After setup finishes, start the app with:

```text
Start-SourceHero.bat
```

The installer creates the Python virtual environment, installs Python dependencies, installs the Electron desktop dependencies, repairs the Electron binary if needed, and runs a smoke check.

## First Run

Once the desktop window opens, you will see a welcome screen if your library is empty.

1. Click `Try the demo (recommended)` to seed a few sample sources, or click `Add my own source` to start fresh.
2. On the `Start` page, run ingestion for one of the sources.
3. Go to `Ask` and ask a question.
4. Optional: open `⚙️ Settings`, paste your OpenAI key, and click `Save`. Answers will be synthesized into a more readable paragraph instead of bullet snippets.

If there are no indexed chunks yet, the app tells you to ingest something first. If a website blocks article fetching, RSS ingestion falls back to the feed summary instead of failing the whole run.

## Configuring OpenAI

You have two options.

### Option 1: Inside the app (recommended)

1. Open the desktop app.
2. Click the `⚙️ Settings` tab.
3. Paste your key in the `OpenAI API Key` field, pick a model, and click `Save`.
4. Click `Test OpenAI connection` to confirm the key works.

The key is written to `user_config.json` inside your platform data directory. It is never committed and never leaves your machine except when the app calls OpenAI on your behalf.

### Option 2: Environment variable

Set `OPENAI_API_KEY` in your shell or `.env`. The env var takes precedence over whatever is saved in the app, which is convenient for switching between accounts during development.

Without a key, SourceHero falls back to local extractive answers with citations.

## Saving Conversations

The `Ask` tab keeps the current conversation in view. After you ask questions, SourceHero generates a Markdown conversation summary with:

- what was discussed
- key answers
- retrieved sources
- the full conversation

Click:

```text
Save Conversation To Knowledge Base
```

The summary is saved as a `conversation` source under `Saved Conversations`, indexed like any other document, and available in future searches.

## Manual Developer Setup

If you want to run it like a normal Python/Node project:

```bash
git clone https://github.com/JeremyL691/SourceHero-AI.git
cd SourceHero-AI

# macOS / Linux
python3.11 -m venv .venv
source .venv/bin/activate

# Windows PowerShell
# py -3.11 -m venv .venv
# .\.venv\Scripts\Activate.ps1

python -m pip install -U pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Optional `.env` values:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
SOURCEHERO_API_PORT=8000
SOURCEHERO_DASHBOARD_PORT=8501
# SOURCEHERO_DATA_DIR=/portable/path   # override the per-user data dir
```

## Running The Desktop App From Terminal

```bash
cd desktop
npm install
npm run dev
```

The desktop app starts:

- FastAPI on `127.0.0.1:8000`
- Streamlit on `127.0.0.1:8501`
- an Electron window pointed at the Streamlit dashboard

Electron installs can be fragile on Windows, so the project includes a repair step:

```bash
npm run ensure-electron
```

`npm run dev` runs that check automatically before launching.

## Browser Mode For Development

Run the backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the dashboard in another terminal:

```bash
streamlit run dashboard/streamlit_app.py
```

Open:

- Dashboard: <http://localhost:8501>
- API docs: <http://127.0.0.1:8000/docs>

## Where Your Data Lives

Starting in v0.4, the database and ingested files live in the standard platform location for application data:

- macOS: `~/Library/Application Support/SourceHero/`
- Windows: `%APPDATA%\SourceHero\`
- Linux: `~/.local/share/SourceHero/`

You can open this directory from the Electron menu: **File → Open Data Folder**. To use a different location (for a portable install, or to keep multiple libraries), set `SOURCEHERO_DATA_DIR`.

If you upgrade from v0.3 and an old `./data/sourcepilot.db` exists, it is copied to the new location automatically on first launch. The original file is left in place so nothing is lost.

## Project Layout

```text
SourceHero-AI/
  app/
    main.py                 # FastAPI app and REST endpoints
    config.py               # Settings and per-user data paths
    database.py             # SQLAlchemy engine/session setup
    models.py               # SQLite models
    schemas.py              # API schemas
    ingestion/              # RSS, webpage, PDF, chunking, cleanup
    retrieval/              # Local retrieval
    services/               # Pipeline, library, citations, conversations, user_settings
    agent/                  # Agent-facing tool wrappers
  dashboard/
    streamlit_app.py        # Streamlit UI
  desktop/
    main.js                 # Electron process manager
    electron-builder.yml    # Packaging config (dmg, nsis)
    scripts/                # Electron repair and smoke checks
  scripts/
    setup-macos.sh          # macOS installer script
    start-macos.sh          # macOS launcher script
    setup-windows.ps1       # Windows installer script
    start-windows.ps1       # Windows launcher script
    build-runtime.sh        # Embed python-build-standalone for release
    build-runtime.ps1
  tests/
  evals/
```

## API Highlights

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Runtime health, stats, OpenAI status |
| `GET` | `/settings` | Read user-configurable settings |
| `POST` | `/settings` | Save OpenAI key and/or model |
| `POST` | `/settings/test-openai` | Verify the configured key actually works |
| `POST` | `/demo/seed` | Add demo sources |
| `POST` | `/sources` | Add RSS, webpage, PDF, or conversation source |
| `GET` | `/sources` | List sources |
| `PATCH` | `/sources/{source_id}` | Update a source |
| `DELETE` | `/sources/{source_id}` | Delete a source and its documents |
| `POST` | `/sources/{source_id}/ingest` | Run ingestion |
| `GET` | `/documents` | Browse documents |
| `GET` | `/documents/{document_id}` | View document detail |
| `GET` | `/documents/{document_id}/chunks` | View document chunks |
| `POST` | `/search` | Ask/search with citations |
| `POST` | `/conversations/save` | Save a Markdown conversation summary |
| `POST` | `/briefings` | Generate a cited briefing |
| `POST` | `/upload-pdf` | Upload a PDF |

Example search:

```bash
curl -s -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What do my sources say about retrieval evaluation?",
    "top_k": 5,
    "source_type": "webpage",
    "tags": ["retrieval"]
  }'
```

## How Answers Work

SourceHero searches indexed chunks and builds answers from retrieved evidence. If it cannot find relevant evidence, it refuses instead of inventing an answer.

When OpenAI synthesis is configured, the model is only given retrieved chunks and is instructed to preserve citations. If synthesis fails for any reason — bad key, rate limit, network — SourceHero falls back to the local cited answer path so the app keeps working.

## Testing

Run the Python test suite:

```bash
pytest
```

Run the desktop smoke check:

```bash
cd desktop
npm run smoke
```

Current coverage includes ingestion, deduplication, citations, library organization, filtered search, onboarding endpoints, dashboard rendering, optional synthesis, conversation saving, cross-platform path resolution, and legacy database migration.

## Roadmap

Things I would like to add next:

- persistent vector search with FAISS or Chroma
- local semantic embeddings
- daily auto-ingestion and scheduled briefings
- saved research prompts
- Markdown/PDF export
- browser extension or clipboard capture
- signed and notarized macOS builds, signed Windows installer
- GitHub Actions for CI and release artifacts

## License

MIT. See [LICENSE](LICENSE).
