# SourceHero AI

SourceHero AI is a local-first knowledge base for people like me who save too many links, PDFs, feeds, notes, and half-finished research threads, then later remember the idea but not where the evidence was.

I did not build this to be another general chatbot. The point is much more practical: keep a reading pile on your own machine, turn it into something searchable, and get answers that stay tied to the sources you actually saved.

Everything runs locally. Your library lives in SQLite on your computer. Webpages, RSS feeds, PDFs, saved conversations, and quick captured notes all end up in the same place. If you add an OpenAI key, SourceHero can produce cleaner synthesized answers and optional semantic search. If you do not, the app still works with local lexical retrieval and citations.

## What It Feels Like To Use

The basic loop is simple:

1. Add a webpage, RSS feed, PDF, or quick capture.
2. Run ingestion so SourceHero cleans, chunks, and indexes the content.
3. Ask a question later and get an answer grounded in the indexed evidence.
4. Save useful conversations back into the library so they become searchable too.

Over time, the library becomes less like a folder of stuff you meant to read and more like a personal reference system you can actually work with.

## What It Can Do Right Now

- Ingest webpages, RSS feeds, PDFs, and saved conversations
- Save quick captures from the clipboard as standalone notes or URL-backed excerpts
- Store everything locally in SQLite
- Organize sources and documents with collections and tags
- Search with filters for source, type, collection, and tags
- Blend lexical search with optional semantic retrieval when an OpenAI key is configured
- Answer questions with citations instead of free-floating guesses
- Generate briefings from indexed evidence
- Save recurring briefing and ingestion schedules while the app is running
- Run as a desktop app through Electron on macOS and Windows
- Let you configure the OpenAI key and model inside the app instead of editing dotfiles

## Current State

This is still an early desktop product, but it is no longer just a prototype. The app has a real backend, a usable UI, cross-platform startup scripts, persistent per-user storage, and a focused automated test suite.

The current release includes:

- FastAPI backend
- Streamlit dashboard
- Electron desktop shell
- SQLite / SQLAlchemy data model
- Hybrid retrieval with local lexical search and optional semantic embeddings
- In-app schedules for recurring ingestion and briefings
- Quick Capture for clipboard-first note and URL saving
- Conversation saving
- Demo seeding for first-run onboarding
- Human-readable ingestion errors for common failures

## What Changed In v0.6

`v0.6.0` is the first version where getting things into the library feels as important as searching them later.

- There is now a proper Quick Capture flow for clipboard-first saving.
- A copied URL can become a webpage source and immediately run ingestion.
- A copied excerpt or note can be saved as a searchable `clip` document without scraping the whole page.
- The desktop menu now has a Quick Capture entry, so saving a note takes fewer steps.
- Clip documents show up in search, documents, and briefings alongside the rest of the library.

More detail lives in [CHANGELOG.md](/Users/jeremyliu/Desktop/Projects/SourceHero-AI/CHANGELOG.md).

## Quick Start

### macOS

Install:

- Python 3.11 or newer
- Node.js LTS

Then open:

```text
Install-SourceHero.command
```

When setup finishes, launch:

```text
Start-SourceHero.command
```

If Gatekeeper complains the first time, right-click and choose **Open**.

### Windows

Install:

- Python 3.11 or newer
- Node.js LTS

Then open:

```text
Install-SourceHero.bat
```

When setup finishes, launch:

```text
Start-SourceHero.bat
```

## First Run

If the library is empty, SourceHero shows a simple welcome flow.

- `Try the demo` seeds a few example sources and indexes them
- `Add my own source` drops you into the normal workflow
- `Skip` opens the app without sample content

The fastest way to understand the product is:

1. Load the demo
2. Open the `Ask` tab
3. Ask a question
4. Inspect the hits and citations
5. Save the conversation back into the library

## OpenAI, Or Not

You do not need an OpenAI key to use SourceHero.

Without one, the app still:

- ingests content
- searches locally
- returns extractive answers with citations

With a key configured, the app can also:

- synthesize more natural answers
- build and use semantic embeddings
- rebuild the local semantic index

You can configure the key either in the Settings tab or through `OPENAI_API_KEY`.

Recommended default model:

```text
OPENAI_MODEL=gpt-5.4-mini
```

## Running It As A Developer

If you want the normal Python + Node workflow:

```bash
git clone https://github.com/JeremyL691/SourceHero-AI.git
cd SourceHero-AI

python3.11 -m venv .venv
source .venv/bin/activate

python -m pip install -U pip
python -m pip install -e ".[dev]"
cp .env.example .env
```

Optional env vars:

```text
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
SOURCEHERO_API_PORT=8000
SOURCEHERO_DASHBOARD_PORT=8501
# SOURCEHERO_DATA_DIR=/portable/path
```

Start the desktop shell:

```bash
cd desktop
npm install
npm run dev
```

Or run the services directly:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
streamlit run dashboard/streamlit_app.py
```

Useful local URLs:

- Dashboard: [http://localhost:8501](http://localhost:8501)
- API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

## Where Data Lives

SourceHero stores user data in the normal per-user app location for each platform.

- macOS: `~/Library/Application Support/SourceHero/`
- Windows: `%APPDATA%\\SourceHero\\`
- Linux: `~/.local/share/SourceHero/`

That directory holds:

- the SQLite database
- raw and processed files
- the local semantic index
- logs
- `user_config.json`

You can override the location with `SOURCEHERO_DATA_DIR`.

## API Highlights

These are the endpoints most people end up touching first:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Runtime health, stats, OpenAI status, semantic index status |
| `GET` | `/index/status` | Local semantic index coverage and readiness |
| `POST` | `/index/rebuild` | Rebuild embeddings for the current chunk corpus |
| `POST` | `/sources` | Add a source |
| `POST` | `/sources/{source_id}/ingest` | Run ingestion |
| `GET` | `/capture/clipboard` | Read and classify clipboard text |
| `POST` | `/captures/parse` | Parse pasted raw capture text |
| `POST` | `/captures` | Save a quick capture or URL |
| `POST` | `/search` | Search / ask with citations |
| `POST` | `/briefings` | Generate a cited briefing |
| `GET` | `/schedules` | List recurring jobs |
| `POST` | `/schedules` | Create a recurring ingest or briefing job |
| `POST` | `/conversations/save` | Save a conversation back into the library |

Example search:

```bash
curl -s -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What do my sources say about retrieval evaluation?",
    "top_k": 5,
    "retrieval_mode": "hybrid",
    "source_type": "webpage",
    "tags": ["retrieval"]
  }'
```

## Testing

Run the Python suite:

```bash
.venv/bin/pytest -q
```

Run the Electron smoke check:

```bash
cd desktop
npm run smoke
```

## Roadmap

Things I still want to add:

- better exports for saved work
- easier capture from the browser or clipboard
- stronger packaging and signing for release builds
- CI and release automation
- more opinionated research workflows once the core storage/retrieval loop is fully settled

## License

MIT. See [LICENSE](/Users/jeremyliu/Desktop/Projects/SourceHero-AI/LICENSE).
