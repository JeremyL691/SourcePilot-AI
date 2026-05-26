# SourceHero AI Project Brief

## One-Sentence Pitch

SourceHero AI is a local-first desktop knowledge base that turns saved webpages, PDFs, RSS feeds, notes, and conversations into a searchable library with cited AI answers.

## Problem

People often save useful research material faster than they can organize it. Browser bookmarks, PDFs, feeds, notes, and pasted excerpts become scattered across tools. Later, the hard part is not asking an AI a question; it is knowing which saved evidence the answer should come from.

## Product Decision

SourceHero is intentionally narrower than a general chatbot. It focuses on one loop:

1. Capture material into a local library.
2. Clean, chunk, deduplicate, and index it.
3. Ask questions against that library.
4. Return answers with inspectable citations.
5. Save useful conversations back into the same knowledge base.

The product remains useful without an OpenAI key by using local lexical retrieval and extractive cited answers. OpenAI improves synthesis and semantic search, but it is not required for the core workflow.

## Architecture

- Electron starts and wraps the local desktop experience.
- Streamlit provides the dashboard UI.
- FastAPI exposes ingestion, search, briefings, schedules, settings, and health endpoints.
- SQLite stores source metadata, documents, chunks, collections, tags, schedules, runs, and saved conversations.
- Local files store raw and processed source content.
- Optional OpenAI calls power synthesized answers and semantic embeddings.

## Engineering Highlights

- Multi-source ingestion for webpages, RSS feeds, PDFs, quick captures, and saved conversations.
- Local-first data model with per-user app storage and no external vector database requirement.
- Hybrid retrieval path that can use lexical search, semantic embeddings, or a blended mode.
- Citation-grounded answers that expose retrieved hits instead of hiding evidence behind generated prose.
- Deduplication and chunking pipeline to keep repeated captures from polluting search results.
- In-app settings for OpenAI key and model selection, with support for environment-based configuration.
- Desktop orchestration through Electron, including backend startup, dashboard startup, data folder access, and a Quick Capture window.
- Tests covering dashboard rendering, ingestion, retrieval, citations, scheduling, settings, deduplication, and pipeline failure behavior.

## Tradeoffs

- Streamlit made the product much faster to build and iterate, but it limits fine-grained UI control compared with a React frontend.
- The current schedule runner works while the app is running; production-grade background scheduling would need a service or launch agent.
- Packaging exists as a desktop shell, but signing, CI releases, and installer polish are still future work.
- The local semantic index keeps the system lightweight, but larger libraries would eventually benefit from a more specialized vector store.

## Next Improvements

- Add polished screenshots and a short demo video for the repository.
- Create a browser capture extension or native share-style capture flow.
- Improve exports for saved answers and briefings.
- Add CI, release automation, and signed desktop builds.
- Build more opinionated research workflows on top of the core capture, index, ask loop.
