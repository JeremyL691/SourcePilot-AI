# SourcePilot AI

SourcePilot AI is a local-first agentic data intelligence platform for building cited answers and briefings from messy public and personal data sources. The v0.1.0 MVP ingests RSS feeds, single webpages, and local PDFs into normalized SQLite records, chunks and deduplicates text, searches indexed evidence with a deterministic local retrieval layer, and generates Markdown answers with citations.

This is intentionally more data-platform than chatbot: ingestion logs, metadata tables, duplicate tracking, source-specific connectors, repeatable tests, and evaluation scaffolding are part of the core product.

## Features

- Add and manage `rss`, `webpage`, and `pdf` sources.
- Run ingestion into explicit `sources`, `documents`, `document_chunks`, `ingestion_runs`, and `briefings` tables.
- Extract text with `feedparser`, `requests` plus `BeautifulSoup`, and `pypdf`.
- Clean, chunk, hash, and deduplicate documents and chunks.
- Search indexed chunks with local TF-IDF style scoring that works without external services.
- Generate extractive answers and briefings with source citations.
- Use a FastAPI backend, OpenAPI docs, and a Streamlit dashboard.
- Run focused pytest coverage and a lightweight retrieval evaluation script.

## Architecture

```text
RSS / Webpage / PDF
        |
        v
Ingestion Connectors
        |
        v
Text Extraction + Cleaning
        |
        v
Chunking + Hash Deduplication
        |
        v
SQLite Metadata + Chunk Store
        |
        v
Local Retrieval Service
        |
        v
Cited Answers + Briefings
        |
        v
FastAPI API + Streamlit Dashboard
```

## Repository Layout

```text
sourcepilot-ai/
  app/
    main.py                 # FastAPI app and endpoints
    config.py               # Local settings and data directories
    database.py             # SQLAlchemy engine/session setup
    models.py               # SQLite data model
    schemas.py              # API request/response schemas
    ingestion/              # RSS, webpage, PDF, chunking, quality checks
    retrieval/              # Deterministic local retrieval
    services/               # Pipeline, citation, briefing services
    agent/                  # Agent-facing tool wrappers
  dashboard/
    streamlit_app.py        # Local dashboard
  evals/
    questions.jsonl         # Evaluation examples
    run_eval.py             # Eval runner
  tests/                    # Focused pytest coverage
  data/                     # Local runtime data, ignored except placeholders
```

## Requirements

- Python 3.11+
- SQLite, included with Python
- Optional: `OPENAI_API_KEY` in `.env` for future synthesis upgrades. v0.1.0 does not require it.

## Setup

```powershell
cd "C:\Users\Jeremy\Desktop\Vibecoding Projects\sourcepilot-ai"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
python -m pip install -e ".[dev]"
copy .env.example .env
```

If `py -3.11` is not available, use any Python 3.11+ executable.

## Run Locally

Start the API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Start the dashboard in a second terminal:

```powershell
streamlit run dashboard/streamlit_app.py
```

Open:

- API docs: <http://127.0.0.1:8000/docs>
- Dashboard: <http://localhost:8501>

## Demo Script

1. Start FastAPI and Streamlit.
2. In the dashboard, add an RSS source such as `https://hnrss.org/frontpage`.
3. Add one webpage URL, for example a documentation page or article.
4. Add a local PDF path or upload a PDF.
5. Select each source and click `Run Ingestion`.
6. Check `Ingestion Runs` for document counts, chunk counts, duplicate skips, and errors.
7. Use `Ask` with a query such as `What do indexed sources say about vector search?`.
8. Use `Briefings` to generate a Markdown briefing for a topic.
9. Run evaluation with `python evals/run_eval.py`.

## API Overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/stats` | Source, document, chunk, and run counts |
| `POST` | `/sources` | Create RSS, webpage, or PDF source |
| `GET` | `/sources` | List sources |
| `POST` | `/sources/{source_id}/ingest` | Run ingestion for one source |
| `GET` | `/ingestion-runs` | List ingestion logs |
| `POST` | `/search` | Search chunks and return cited answer |
| `POST` | `/briefings` | Generate and save cited briefing |
| `GET` | `/briefings` | List briefing history |
| `POST` | `/upload-pdf` | Upload a PDF and create a source |

Create an RSS source:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/sources `
  -ContentType "application/json" `
  -Body '{"source_type":"rss","name":"HN Front Page","url":"https://hnrss.org/frontpage"}'
```

Run ingestion:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/sources/1/ingest
```

Search with citations:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/search `
  -ContentType "application/json" `
  -Body '{"query":"What does the indexed evidence say about AI agents?","top_k":5}'
```

Generate a briefing:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/briefings `
  -ContentType "application/json" `
  -Body '{"topic":"AI data engineering","top_k":8}'
```

## Data Model

- `sources`: source type, name, URL or local path, status, creation time, last ingestion time.
- `documents`: source-level extracted records with raw and cleaned text plus content hashes.
- `document_chunks`: searchable chunks with chunk hashes, token estimates, metadata JSON, and embedding IDs.
- `ingestion_runs`: run status, inserted document/chunk counts, duplicate counts, and error messages.
- `briefings`: saved Markdown briefings and citation metadata.

Runtime data is local:

- `data/sourcepilot.db`: SQLite database.
- `data/raw`: uploaded PDFs and raw inputs.
- `data/processed`: reserved for generated manifests.
- `data/vector_index`: reserved for future Chroma/FAISS files.

## Retrieval And Citation Behavior

v0.1.0 uses a deterministic local TF-IDF style search over stored chunks. This keeps the MVP usable without API keys, model downloads, or vector database setup. If no relevant indexed chunks are found, the app refuses to answer instead of filling gaps with general knowledge.

Answers use this citation shape:

```markdown
Based only on indexed evidence:
- Retrieved evidence snippet. [1]

Sources:
[1] Source Title - URL or local PDF page
```

## Testing

```powershell
pytest
```

Current focused coverage:

- Chunk cleaning and overlap behavior.
- Duplicate document/chunk skipping.
- RSS parsing from sample feed XML.
- Citation formatting and unsupported-answer behavior.

Run the lightweight retrieval evaluation:

```powershell
python evals/run_eval.py
```

The report is written to `evals/eval_report.md`.

## Roadmap

- Add persistent Chroma or FAISS as an optional retrieval backend while keeping lexical fallback.
- Add LangGraph as the visible agent orchestration layer once routing grows beyond the current tool wrappers.
- Reuse PDF outline/table-of-contents extraction patterns from `PDFSplitter`.
- Reuse full-article extraction and RSS summarization patterns from `MyNewsAlarm`.
- Add API-source ingestion for domain-specific data feeds.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
