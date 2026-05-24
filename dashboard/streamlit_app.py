from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st


def _humanize_path(path: str | None) -> str:
    if not path:
        return "—"
    home = os.path.expanduser("~")
    if path.startswith(home):
        return "~" + path[len(home):]
    return path


API_BASE = os.getenv("SOURCEHERO_API_BASE", "http://127.0.0.1:8000")
SEARCHABLE_SOURCE_TYPES = ["", "rss", "webpage", "pdf", "conversation"]
ADDABLE_SOURCE_TYPES = ["rss", "webpage", "pdf"]
_BUTTON_COUNTER = 0

st.set_page_config(page_title="SourceHero AI", layout="wide")
st.title("SourceHero AI")
st.caption("A local personal knowledge base that answers from your own sources.")


def api_get(path: str, params: dict | None = None):
    response = requests.get(f"{API_BASE}{path}", params=_clean_params(params), timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None, files: dict | None = None, params: dict | None = None):
    if files:
        response = requests.post(f"{API_BASE}{path}", params=params, files=files, timeout=120)
    else:
        response = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=120)
    response.raise_for_status()
    return response.json()


def api_patch(path: str, payload: dict):
    response = requests.patch(f"{API_BASE}{path}", json={k: v for k, v in payload.items() if v not in ("", None)}, timeout=60)
    response.raise_for_status()
    return response.json()


def api_delete(path: str, params: dict | None = None):
    response = requests.delete(f"{API_BASE}{path}", params=_clean_params(params), timeout=60)
    response.raise_for_status()
    return response.json()


def _clean_params(params: dict | None) -> dict:
    clean: dict = {}
    for key, value in (params or {}).items():
        if value in (None, "", []):
            continue
        clean[key] = value
    return clean


def _options(items: list[dict], label_key: str = "name") -> dict[str, int]:
    return {f"{item['id']} - {item[label_key]}": item["id"] for item in items}


def _next_button_key(label: str) -> str:
    global _BUTTON_COUNTER
    _BUTTON_COUNTER += 1
    safe_label = "".join(char.lower() if char.isalnum() else "_" for char in label).strip("_")
    return f"button_{safe_label}_{_BUTTON_COUNTER}"


def _button(label: str, *, key: str | None = None, button_type: str = "secondary", **kwargs):
    return st.button(label, type=button_type, key=key or _next_button_key(label), **kwargs)


def _friendly_error(exc: Exception) -> str:
    """Turn a backend / network exception into something a non-developer can act on."""
    text = str(exc)
    lowered = text.lower()
    if isinstance(exc, requests.ConnectionError) or "connection" in lowered or "max retries" in lowered:
        return "Cannot reach the backend. Make sure SourceHero is running (restart the desktop app)."
    if isinstance(exc, requests.Timeout) or "timeout" in lowered or "timed out" in lowered:
        return "Request timed out. The network may be slow or the target site is not responding. Try again."
    if "name or service not known" in lowered or "nodename nor servname" in lowered:
        return "Could not resolve URL (DNS failure). Check spelling and your network connection."
    if "ssl" in lowered or "certificate" in lowered:
        return "SSL certificate error. The target site's certificate may be invalid."
    if "403" in text or "401" in text:
        return "Access denied (403/401). The site may be blocking automated readers."
    if "404" in text:
        return "Page not found (404). Check that the URL is correct."
    if "pdf" in lowered and ("encrypted" in lowered or "decrypt" in lowered):
        return "PDF is encrypted and cannot be parsed."
    return text


def _safe_action(label: str, action, success: str | None = None, button_type: str = "secondary", key: str | None = None):
    if _button(label, key=key, button_type=button_type):
        try:
            result = action()
            if success:
                st.success(success)
            return result
        except requests.HTTPError as exc:
            try:
                detail = exc.response.json().get("detail")
            except Exception:
                detail = exc.response.text
            st.error(detail or _friendly_error(exc))
        except Exception as exc:
            st.error(_friendly_error(exc))
    return None


def _init_chat_state() -> None:
    st.session_state.setdefault("chat_history", [])
    st.session_state.setdefault("conversation_markdown", "")


def _conversation_title() -> str:
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            return message["content"][:80] or "Saved Conversation"
    return "Saved Conversation"


def _build_conversation_markdown() -> str:
    title = _conversation_title()
    lines = [
        f"# Conversation Summary: {title}",
        "",
        "## What Was Discussed",
    ]
    for index, message in enumerate(st.session_state.chat_history, start=1):
        if message["role"] == "user":
            lines.append(f"- Question {index}: {message['content']}")
    lines.extend(["", "## Key Answers"])
    for message in st.session_state.chat_history:
        if message["role"] == "assistant":
            answer = message["content"].replace("\r\n", "\n").strip()
            lines.append(answer)
            lines.append("")
    lines.extend(["## Retrieved Sources"])
    seen: set[str] = set()
    for message in st.session_state.chat_history:
        for hit in message.get("hits", []):
            label = f"{hit.get('citation', '')} {hit.get('title', '')} - {hit.get('url') or hit.get('local_path') or hit.get('source_name', '')}".strip()
            if label and label not in seen:
                seen.add(label)
                lines.append(f"- {label}")
    if not seen:
        lines.append("- No retrieved sources were attached to this conversation.")
    lines.extend(["", "## Full Conversation"])
    for message in st.session_state.chat_history:
        speaker = "User" if message["role"] == "user" else "SourceHero AI"
        lines.extend([f"### {speaker}", message["content"].strip(), ""])
    return "\n".join(lines).strip()


try:
    health = api_get("/health")
    stats = health["stats"]
except Exception as exc:
    st.error(f"SourceHero backend is not running at {API_BASE}. Start the desktop app or run the API first.")
    st.caption(_friendly_error(exc) if "_friendly_error" in globals() else str(exc))
    st.stop()

collections = api_get("/collections")
tags = api_get("/tags")
sources = api_get("/sources")
runs = api_get("/ingestion-runs")
_init_chat_state()

with st.sidebar:
    st.markdown("### 🦸 SourceHero")
    st.caption("Local-first personal knowledge base")
    st.divider()
    st.metric("Sources", stats.get("sources", 0))
    st.metric("Documents", stats.get("documents", 0))
    st.metric("Chunks", stats.get("chunks", 0))
    st.divider()
    st.caption(f"API: {API_BASE}")
    st.caption(f"Data: {_humanize_path(health.get('data_dir'))}", help=health.get("data_dir") or "")
    if health.get("openai_configured"):
        preview = health.get("openai_key_preview") or "set"
        source_label = "env" if health.get("openai_key_source") == "env" else "in-app"
        st.success(f"✅ OpenAI key configured ({preview}, from {source_label})")
    else:
        st.info("💡 Add an OpenAI API key in the **Settings** tab for nicer synthesized answers.")

# First-run welcome: takes over when knowledge base is brand new and user hasn't dismissed.
if stats["sources"] == 0 and not st.session_state.get("welcome_dismissed"):
    st.markdown("## 👋 Welcome to SourceHero AI")
    st.markdown(
        "Looks like this is your first time. Three steps to get going:\n\n"
        "1. **Try the demo** (recommended) — one click loads example sources\n"
        "2. **Add your own source** — paste an RSS / webpage URL or upload a PDF\n"
        "3. **Ask questions** — head to the *Ask* tab and ask anything"
    )
    welcome_cols = st.columns([1, 1, 1])
    with welcome_cols[0]:
        if st.button("🚀 Try the demo (recommended)", type="primary", use_container_width=True, key="welcome_demo"):
            try:
                with st.spinner("Loading demo content and indexing… (this can take 20–60s)"):
                    result = api_post("/demo/seed-and-ingest")
                ok_count = sum(1 for r in result.get("ingestion", []) if r["status"] == "success")
                total = len(result.get("ingestion", []))
                chunks = result.get("total_chunks_inserted", 0)
                if chunks > 0:
                    st.success(f"Indexed {chunks} chunks from {ok_count}/{total} demo sources. Head to the **Ask** tab.")
                else:
                    st.warning(
                        f"Demo sources were added but none could be indexed right now "
                        f"(network or blocked by the sites). You can retry from the Sources tab."
                    )
                st.session_state["welcome_dismissed"] = True
                st.rerun()
            except Exception as exc:
                st.error(f"Could not load demo: {_friendly_error(exc)}")
    with welcome_cols[1]:
        if st.button("➕ Add my own source", use_container_width=True, key="welcome_add"):
            st.session_state["welcome_dismissed"] = True
            st.session_state["scroll_to_add_source"] = True
            st.rerun()
    with welcome_cols[2]:
        if st.button("Skip", use_container_width=True, key="welcome_skip"):
            st.session_state["welcome_dismissed"] = True
            st.rerun()
    st.divider()

metric_cols = st.columns(4)
for col, key in zip(metric_cols, ["sources", "documents", "chunks", "ingestion_runs"]):
    col.metric(key.replace("_", " ").title(), stats.get(key, 0))

tab_start, tab_sources, tab_ask, tab_documents, tab_briefings, tab_runs, tab_advanced, tab_settings = st.tabs(
    ["Start", "Sources", "Ask", "Documents", "Briefings", "Runs", "Advanced Library", "⚙️ Settings"]
)

with tab_start:
    st.header("Start in three steps")
    if st.session_state.pop("scroll_to_add_source", False):
        st.info("👇 Add your first source under **Step 1** below.")
    if stats["sources"] == 0:
        st.info("Your knowledge base is empty. Load demo sources or add your own first source.")
        start_cols = st.columns(2)
        with start_cols[0]:
            if _button("Load Demo Sources", key="start_load_demo_sources", button_type="primary"):
                try:
                    result = api_post("/demo/seed")
                    st.success(result["message"])
                    st.rerun()
                except Exception as exc:
                    st.error(f"Could not load demo sources: {exc}")
        with start_cols[1]:
            st.write("Prefer your own material? Add a webpage, RSS feed, or PDF below.")
    elif stats["chunks"] == 0:
        st.warning("Sources exist, but nothing has been indexed yet. Run ingestion for one source to unlock search.")
    else:
        st.success("Your knowledge base is ready. Ask a question below or continue adding sources.")

    step_add, step_ingest, step_ask = st.columns(3)
    with step_add:
        st.subheader("1. Add source")
        source_type = st.selectbox("Source type", ["webpage", "rss", "pdf"], key="start_source_type")
        source_name = st.text_input("Name", key="start_source_name")
        if source_type in {"webpage", "rss"}:
            source_url = st.text_input("URL", key="start_source_url", placeholder="https://example.com/article")
            _safe_action(
                "Add Source",
                lambda: api_post("/sources", {"source_type": source_type, "name": source_name or source_url, "url": source_url}),
                "Source added. Run ingestion next.",
                "primary",
                key="start_add_url_source",
            )
        else:
            uploaded = st.file_uploader("Upload PDF", type=["pdf"], key="start_pdf")
            if uploaded:
                _safe_action(
                    "Upload PDF",
                    lambda: api_post(
                        "/upload-pdf",
                        files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                        params={"name": source_name or uploaded.name},
                    ),
                    "PDF uploaded. Run ingestion next.",
                    "primary",
                    key="start_upload_pdf",
                )
    with step_ingest:
        st.subheader("2. Index content")
        source_options = _options(sources)
        if source_options:
            selected_source = st.selectbox("Choose source", source_options.keys(), key="start_ingest_source")
            source_id = source_options[selected_source]
            result = _safe_action(
                "Run Ingestion",
                lambda: api_post(f"/sources/{source_id}/ingest"),
                None,
                "primary",
                key="start_run_ingestion",
            )
            if result:
                st.success(f"{result['status']}: {result['documents_inserted']} docs, {result['chunks_inserted']} chunks, {result['duplicates_skipped']} duplicates.")
                st.rerun()
        else:
            st.caption("Add a source first.")
    with step_ask:
        st.subheader("3. Ask")
        question = st.text_area("Question", key="start_question", placeholder="What does my knowledge base say about this topic?")
        if _button("Ask Now", key="start_ask_now", button_type="primary", disabled=stats["chunks"] == 0 or not question):
            try:
                result = api_post("/search", {"query": question, "top_k": 5})
                if result["hits"]:
                    st.markdown(result["answer_markdown"])
                else:
                    st.warning("No matching indexed evidence yet. Add or ingest relevant sources first.")
            except Exception as exc:
                st.error(str(exc))

    latest = runs[0] if runs else None
    if latest:
        st.divider()
        st.subheader("Latest ingestion")
        st.write(
            f"Status: `{latest['status']}` | Documents: `{latest['documents_inserted']}/{latest['documents_found']}` | "
            f"Chunks: `{latest['chunks_inserted']}` | Duplicates: `{latest['duplicates_skipped']}`"
        )
        if latest.get("error_message"):
            st.warning(
                "The latest ingestion could not fetch one or more sources. Some websites block automated reading. "
                "Try another source, upload a PDF, or rerun ingestion later."
            )
            st.caption(latest["error_message"])

with tab_sources:
    st.header("Sources")
    add_col, manage_col = st.columns([1, 2])
    with add_col:
        st.subheader("Add Source")
        source_type = st.selectbox("Type", ADDABLE_SOURCE_TYPES)
        source_name = st.text_input("Source name")
        if source_type in {"rss", "webpage"}:
            source_url = st.text_input("URL")
            _safe_action(
                "Add Source",
                lambda: api_post("/sources", {"source_type": source_type, "name": source_name or source_url, "url": source_url}),
                "Source added.",
                "primary",
                key="sources_add_url_source",
            )
        else:
            local_path = st.text_input("Local PDF path")
            uploaded = st.file_uploader("Or upload PDF", type=["pdf"])
            if uploaded:
                _safe_action(
                    "Upload PDF",
                    lambda: api_post(
                        "/upload-pdf",
                        files={"file": (uploaded.name, uploaded.getvalue(), "application/pdf")},
                        params={"name": source_name or uploaded.name},
                    ),
                    "PDF uploaded.",
                    "primary",
                    key="sources_upload_pdf",
                )
            if local_path:
                _safe_action(
                    "Add Local PDF",
                    lambda: api_post("/sources", {"source_type": "pdf", "name": source_name or Path(local_path).stem, "local_path": local_path}),
                    "PDF source added.",
                    key="sources_add_local_pdf",
                )
    with manage_col:
        st.subheader("Manage Sources")
        st.dataframe(
            sources,
            width="stretch",
            hide_index=True,
            column_config={
                "id": None,
                "url": st.column_config.LinkColumn("URL", display_text="open"),
                "local_path": None,
                "created_at": None,
                "last_ingested_at": st.column_config.DatetimeColumn("Last indexed", format="MMM D, h:mm A"),
                "source_type": st.column_config.TextColumn("Type"),
                "name": st.column_config.TextColumn("Name", width="large"),
                "status": st.column_config.TextColumn("Status"),
            },
            column_order=["name", "source_type", "status", "url", "last_ingested_at"],
        )
        source_options = _options(sources)
        if source_options:
            selected = st.selectbox("Manage source", source_options.keys())
            source_id = source_options[selected]
            current = next(item for item in sources if item["id"] == source_id)
            action_cols = st.columns(4)
            if action_cols[0].button("Run Ingestion", key=f"source_{source_id}_run_ingestion"):
                try:
                    run = api_post(f"/sources/{source_id}/ingest")
                    st.success(f"{run['status']}: +{run['chunks_inserted']} chunks, {run['duplicates_skipped']} duplicates skipped")
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
            if action_cols[1].button("Pause", key=f"source_{source_id}_pause"):
                api_patch(f"/sources/{source_id}", {"status": "paused"})
                st.rerun()
            if action_cols[2].button("Activate", key=f"source_{source_id}_activate"):
                api_patch(f"/sources/{source_id}", {"status": "active"})
                st.rerun()
            if action_cols[3].button("Delete Source", key=f"source_{source_id}_delete"):
                api_delete(f"/sources/{source_id}")
                st.rerun()
            with st.expander("Edit metadata and advanced organization"):
                new_name = st.text_input("Name", current["name"])
                new_url = st.text_input("URL", current.get("url") or "")
                new_path = st.text_input("Local path", current.get("local_path") or "")
                if _button("Save Source", key=f"source_{source_id}_save"):
                    api_patch(f"/sources/{source_id}", {"name": new_name, "url": new_url, "local_path": new_path})
                    st.rerun()
                if collections:
                    selected_collection = st.selectbox("Add source to collection", _options(collections).keys())
                    if _button("Attach Source To Collection", key=f"source_{source_id}_attach_collection"):
                        api_post(f"/collections/{_options(collections)[selected_collection]}/items", {"item_type": "source", "item_id": source_id})
                        st.rerun()
                if tags:
                    selected_tag = st.selectbox("Add tag to source", _options(tags).keys())
                    if _button("Attach Tag To Source", key=f"source_{source_id}_attach_tag"):
                        api_post(f"/tags/{_options(tags)[selected_tag]}/items", {"item_type": "source", "item_id": source_id})
                        st.rerun()

with tab_ask:
    st.header("Ask your knowledge base")
    if stats["chunks"] == 0:
        st.warning("No indexed chunks yet. Add a source and run ingestion from the Start page first.")

    if st.session_state.chat_history:
        st.subheader("Conversation")
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    query = st.text_area("Question", placeholder="What do my saved sources say about retrieval evaluation?")
    ask_cols = st.columns(4)
    top_k = ask_cols[0].slider("Top K", 1, 12, 5)
    ask_source_type = ask_cols[1].selectbox("Type filter", SEARCHABLE_SOURCE_TYPES)
    ask_collection_options = {"": None} | _options(collections)
    ask_collection = ask_cols[2].selectbox("Collection filter", ask_collection_options.keys())
    ask_tags = ask_cols[3].multiselect("Tag filter", [tag["name"] for tag in tags])
    if _button("Ask", key="ask_submit", button_type="primary", disabled=not query or stats["chunks"] == 0):
        result = api_post(
            "/search",
            {
                "query": query,
                "top_k": top_k,
                "source_type": ask_source_type or None,
                "collection_id": ask_collection_options[ask_collection],
                "tags": ask_tags,
            },
        )
        if result["hits"]:
            st.session_state.chat_history.append({"role": "user", "content": query})
            st.session_state.chat_history.append(
                {"role": "assistant", "content": result["answer_markdown"], "hits": result["hits"]}
            )
            st.session_state.conversation_markdown = _build_conversation_markdown()
            st.markdown(result["answer_markdown"])
            st.dataframe(result["hits"], width="stretch", hide_index=True)
        else:
            st.warning("No matching indexed evidence. Try a broader query or ingest more sources.")

    if st.session_state.chat_history:
        st.divider()
        st.subheader("Markdown Conversation Summary")
        if not st.session_state.conversation_markdown:
            st.session_state.conversation_markdown = _build_conversation_markdown()
        st.text_area("Generated markdown", st.session_state.conversation_markdown, height=280, key="conversation_summary_preview")
        save_cols = st.columns(2)
        if save_cols[0].button("Save Conversation To Knowledge Base", key="save_conversation_to_kb", type="primary"):
            try:
                saved = api_post(
                    "/conversations/save",
                    {"title": _conversation_title(), "markdown": st.session_state.conversation_markdown},
                )
                if saved["documents_inserted"]:
                    st.success("Conversation saved and indexed in your knowledge base.")
                else:
                    st.info("This conversation was already saved. No duplicate document was created.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        if save_cols[1].button("Clear Conversation", key="clear_conversation"):
            st.session_state.chat_history = []
            st.session_state.conversation_markdown = ""
            st.rerun()

with tab_documents:
    st.header("Documents")
    filter_cols = st.columns(4)
    source_type_filter = filter_cols[0].selectbox("Source type", SEARCHABLE_SOURCE_TYPES)
    collection_filter_options = {"": None} | _options(collections)
    collection_filter = filter_cols[1].selectbox("Collection", collection_filter_options.keys())
    tag_filter_names = filter_cols[2].multiselect("Tags", [tag["name"] for tag in tags])
    source_filter_options = {"": None} | _options(sources)
    source_filter = filter_cols[3].selectbox("Source", source_filter_options.keys())
    params = {
        "source_type": source_type_filter,
        "collection_id": collection_filter_options[collection_filter],
        "tags": tag_filter_names,
        "source_ids": [source_filter_options[source_filter]] if source_filter_options[source_filter] else None,
    }
    documents = api_get("/documents", params=params)
    if not documents:
        st.info("No documents match these filters yet.")
    else:
        st.dataframe(documents, width="stretch", hide_index=True)
        selected_document = st.selectbox("Open document", _options(documents, "title").keys())
        document_id = _options(documents, "title")[selected_document]
        doc = api_get(f"/documents/{document_id}")
        st.markdown(f"### {doc['title']}")
        st.caption(f"Source: {doc.get('source_name')} | Type: {doc.get('source_type')} | URL: {doc.get('url') or ''}")
        with st.expander("Advanced organization"):
            if collections:
                selected_collection = st.selectbox("Add document to collection", _options(collections).keys(), key="doc_collection")
                if _button("Attach Document To Collection", key=f"document_{document_id}_attach_collection"):
                    api_post(f"/collections/{_options(collections)[selected_collection]}/items", {"item_type": "document", "item_id": document_id})
                    st.rerun()
            if tags:
                selected_tag = st.selectbox("Add tag to document", _options(tags).keys(), key="doc_tag")
                if _button("Attach Tag To Document", key=f"document_{document_id}_attach_tag"):
                    api_post(f"/tags/{_options(tags)[selected_tag]}/items", {"item_type": "document", "item_id": document_id})
                    st.rerun()
        st.text_area("Clean text", doc.get("clean_text") or "", height=260)
        with st.expander("Chunks"):
            st.dataframe(api_get(f"/documents/{document_id}/chunks"), width="stretch", hide_index=True)

with tab_briefings:
    st.header("Briefings")
    topic = st.text_input("Briefing topic", placeholder="AI data engineering")
    briefing_k = st.slider("Evidence count", 3, 15, 8)
    if _button("Generate Briefing", key="briefings_generate", button_type="primary") and topic:
        briefing = api_post("/briefings", {"topic": topic, "top_k": briefing_k})
        st.markdown(briefing["answer_markdown"])
    st.dataframe(api_get("/briefings"), width="stretch", hide_index=True)

with tab_runs:
    st.header("Ingestion Runs")
    st.dataframe(runs, width="stretch", hide_index=True)
    failures = [run for run in runs if run["status"] == "failed"]
    if failures:
        st.warning(f"{len(failures)} ingestion run(s) need attention. Check error_message for details.")

with tab_advanced:
    st.header("Advanced Library")
    st.caption("Collections and tags are optional. Use them when your library grows.")
    left, right = st.columns(2)
    with left:
        st.subheader("Collections")
        with st.form("create_collection"):
            name = st.text_input("Collection name")
            description = st.text_area("Description")
            if st.form_submit_button("Create Collection", type="primary"):
                api_post("/collections", {"name": name, "description": description})
                st.rerun()
        st.dataframe(collections, width="stretch", hide_index=True)
        collection_options = _options(collections)
        if collection_options:
            selected = st.selectbox("Edit collection", collection_options.keys())
            collection_id = collection_options[selected]
            current = next(item for item in collections if item["id"] == collection_id)
            new_name = st.text_input("New collection name", current["name"])
            new_description = st.text_area("New description", current.get("description") or "")
            c1, c2 = st.columns(2)
            if c1.button("Save Collection", key=f"collection_{collection_id}_save"):
                api_patch(f"/collections/{collection_id}", {"name": new_name, "description": new_description})
                st.rerun()
            if c2.button("Delete Collection", key=f"collection_{collection_id}_delete"):
                api_delete(f"/collections/{collection_id}")
                st.rerun()
    with right:
        st.subheader("Tags")
        with st.form("create_tag"):
            tag_name = st.text_input("Tag name")
            color = st.text_input("Color", placeholder="#4f46e5")
            if st.form_submit_button("Create Tag", type="primary"):
                api_post("/tags", {"name": tag_name, "color": color or None})
                st.rerun()
        st.dataframe(tags, width="stretch", hide_index=True)
        tag_options = _options(tags)
        if tag_options:
            selected = st.selectbox("Edit tag", tag_options.keys())
            tag_id = tag_options[selected]
            current = next(item for item in tags if item["id"] == tag_id)
            new_name = st.text_input("New tag name", current["name"])
            new_color = st.text_input("New color", current.get("color") or "")
            t1, t2 = st.columns(2)
            if t1.button("Save Tag", key=f"tag_{tag_id}_save"):
                api_patch(f"/tags/{tag_id}", {"name": new_name, "color": new_color})
                st.rerun()
            if t2.button("Delete Tag", key=f"tag_{tag_id}_delete"):
                api_delete(f"/tags/{tag_id}")
                st.rerun()

with tab_settings:
    st.header("Settings")
    st.caption("API keys and model choice. Stored in your local data directory — never sent anywhere except OpenAI when you ask a question.")

    current_settings = api_get("/settings")
    st.subheader("OpenAI")

    if current_settings.get("openai_configured"):
        preview = current_settings.get("openai_key_preview") or "set"
        source = current_settings.get("openai_key_source")
        st.success(f"OpenAI key is configured ({preview}, from {source}).")
        if source == "env":
            st.caption("This key comes from the OPENAI_API_KEY environment variable. To change it, edit `.env` and restart, or override it below.")
    else:
        st.info("No OpenAI key configured. The app still works using local extractive answers — adding a key just makes answers more readable.")

    with st.form("openai_settings_form"):
        new_key = st.text_input(
            "OpenAI API Key",
            value="",
            type="password",
            placeholder="sk-...",
            help="Get one at https://platform.openai.com/api-keys",
        )
        model_choices = ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini", "gpt-4o", "gpt-5-mini"]
        current_model = current_settings.get("openai_model") or "gpt-4.1-mini"
        # Preserve a custom / unknown model name by prepending it instead of silently resetting.
        if current_model not in model_choices:
            model_choices = [current_model] + model_choices
        new_model = st.selectbox(
            "Model",
            model_choices,
            index=model_choices.index(current_model),
            help="`gpt-4.1-mini` is the recommended default — fast and inexpensive.",
        )
        col_save, col_clear = st.columns([1, 1])
        save_clicked = col_save.form_submit_button("💾 Save", type="primary", use_container_width=True)
        clear_clicked = col_clear.form_submit_button("🗑️ Clear API key", use_container_width=True)

    if save_clicked:
        payload: dict = {"openai_model": new_model}
        if new_key.strip():
            payload["openai_api_key"] = new_key.strip()
        try:
            api_post("/settings", payload)
            st.success("Settings saved. Refreshing…")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not save settings: {_friendly_error(exc)}")

    if clear_clicked:
        try:
            api_post("/settings", {"openai_api_key": ""})
            st.success("API key cleared.")
            st.rerun()
        except Exception as exc:
            st.error(f"Could not clear API key: {_friendly_error(exc)}")

    if current_settings.get("openai_configured"):
        st.divider()
        if st.button("🔌 Test OpenAI connection", key="settings_test_openai"):
            with st.spinner("Calling OpenAI…"):
                try:
                    result = api_post("/settings/test-openai")
                    st.success(f"OK — model `{result.get('model')}` replied: “{result.get('sample')}”")
                except requests.HTTPError as exc:
                    try:
                        detail = exc.response.json().get("detail")
                    except Exception:
                        detail = exc.response.text
                    st.error(detail or _friendly_error(exc))
                except Exception as exc:
                    st.error(_friendly_error(exc))

    st.divider()
    st.subheader("Data directory")
    st.code(current_settings.get("data_dir") or "—", language="text")
    st.caption("All your sources, indexed documents, and this config file live here.")
