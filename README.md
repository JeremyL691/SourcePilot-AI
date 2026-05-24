# SourcePilot AI

SourcePilot AI is a local-first personal knowledge base for people who save a lot of links, PDFs, feeds, notes, and research conversations, then forget where the useful parts went.

I built it to answer a simple question: what if my reading pile could turn into a searchable, cited knowledge base on my own computer, without needing to set up a cloud database or a paid AI workflow first?

The app runs locally on Windows, stores data in SQLite, ingests webpages/RSS/PDFs, lets you organize sources with collections and tags, and answers questions using only the evidence it has indexed. If OpenAI credentials are available, it can synthesize a nicer answer. If not, it still works fully offline with local extractive answers and citations.

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
- Stay usable without an OpenAI API key.

## Current Status

This is an early but usable desktop version. The goal is not to be another generic chatbot. The goal is to become a practical personal knowledge workspace: collect information, keep it organized, ask questions later, and preserve useful conversations as reusable notes.

The current version includes:

- FastAPI backend
- SQLite/SQLAlchemy data model
- Streamlit dashboard
- Electron desktop shell
- RSS, webpage, PDF, and saved conversation ingestion
- Local TF-IDF style retrieval
- Cited answers and briefings
- Collections and tags
- Demo source seeding
- Windows setup/start scripts
- Focused automated tests

## Quick Start On Windows

Install the two system dependencies first:

- Python 3.11 or newer  
  When installing Python, check `Add python.exe to PATH`.

- Node.js LTS  
  The default installer options are fine.

Then clone or open the project folder and double-click:

```text
Install-SourcePilot.bat
```

After setup finishes, start the app with:

```text
Start-SourcePilot.bat
```

That is the recommended path for normal use. The installer creates the Python virtual environment, installs Python dependencies, installs the Electron desktop dependencies, repairs the Electron binary if needed, and runs a smoke check.

## First Run

Once the desktop window opens:

1. Go to `Start`.
2. Click `Load Demo Sources`, or add your own webpage/RSS/PDF.
3. Click `Run Ingestion`.
4. Go to `Ask`.
5. Ask a question about the indexed material.

If there are no indexed chunks yet, the app will tell you to ingest something first. If a website blocks article fetching, RSS ingestion falls back to the feed summary instead of failing the whole run.

## Saving Conversations

The `Ask` tab now keeps the current conversation in view. After you ask questions, SourcePilot generates a Markdown conversation summary with:

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

```powershell
cd sourcepilot-ai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
copy .env.example .env
```

Optional `.env` values:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
SOURCEPILOT_API_PORT=8000
SOURCEPILOT_DASHBOARD_PORT=8501
```

Without `OPENAI_API_KEY` and `OPENAI_MODEL`, SourcePilot uses local extractive answers.

## Running The Desktop App From Terminal

```powershell
cd sourcepilot-ai\desktop
npm.cmd install
npm.cmd run dev
```

The desktop app starts:

- FastAPI on `127.0.0.1:8000`
- Streamlit on `127.0.0.1:8501`
- an Electron window pointed at the Streamlit dashboard

Electron installs can be fragile on Windows, so the project includes a repair step:

```powershell
npm.cmd run ensure-electron
```

`npm.cmd run dev` runs that check automatically before launching.

## Browser Mode For Development

Run the backend:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run the dashboard in another terminal:

```powershell
streamlit run dashboard/streamlit_app.py
```

Open:

- Dashboard: <http://localhost:8501>
- API docs: <http://127.0.0.1:8000/docs>

## Project Layout

```text
sourcepilot-ai/
  app/
    main.py                 # FastAPI app and REST endpoints
    config.py               # Settings and local data paths
    database.py             # SQLAlchemy engine/session setup
    models.py               # SQLite models
    schemas.py              # API schemas
    ingestion/              # RSS, webpage, PDF, chunking, cleanup
    retrieval/              # Local retrieval
    services/               # Pipeline, library, citations, conversations
    agent/                  # Agent-facing tool wrappers
  dashboard/
    streamlit_app.py        # Streamlit UI
  desktop/
    main.js                 # Electron process manager
    scripts/                # Electron repair and smoke checks
  scripts/
    setup-windows.ps1       # Windows installer script
    start-windows.ps1       # Windows launcher script
  tests/
  evals/
  data/
```

Runtime data lives locally:

```text
data/sourcepilot.db
data/raw/
data/processed/
data/vector_index/
```

## API Highlights

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Runtime health and stats |
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

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/search `
  -ContentType "application/json" `
  -Body '{
    "query": "What do my sources say about retrieval evaluation?",
    "top_k": 5,
    "source_type": "webpage",
    "tags": ["retrieval"]
  }'
```

## How Answers Work

SourcePilot searches indexed chunks and builds answers from retrieved evidence. If it cannot find relevant evidence, it refuses instead of inventing an answer.

When OpenAI synthesis is configured, the model is only given retrieved chunks and is instructed to preserve citations. If synthesis fails, SourcePilot falls back to the local cited answer path.

## Testing

Run the Python test suite:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Run the desktop smoke check:

```powershell
cd desktop
npm.cmd run smoke
```

Current coverage includes ingestion, deduplication, citations, library organization, filtered search, onboarding endpoints, dashboard rendering, optional synthesis, and conversation saving.

## Roadmap

Things I would like to add next:

- daily auto-ingestion
- scheduled briefings
- saved research prompts
- Markdown/PDF export
- persistent vector search with FAISS or Chroma
- local semantic embeddings
- browser extension or clipboard capture
- packaged Windows installer
- GitHub Actions and a demo dataset

## License

MIT. See [LICENSE](LICENSE).
