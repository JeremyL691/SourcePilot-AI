from __future__ import annotations

import os
from pathlib import Path

import requests
import streamlit as st


API_BASE = os.getenv("SOURCEPILOT_API_BASE", "http://127.0.0.1:8000")


st.set_page_config(page_title="SourcePilot AI", layout="wide")
st.title("SourcePilot AI")


def api_get(path: str):
    response = requests.get(f"{API_BASE}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict | None = None):
    response = requests.post(f"{API_BASE}{path}", json=payload or {}, timeout=60)
    response.raise_for_status()
    return response.json()


stats_cols = st.columns(4)
try:
    stats = api_get("/stats")
    for col, key in zip(stats_cols, ["sources", "documents", "chunks", "ingestion_runs"]):
        col.metric(key.replace("_", " ").title(), stats.get(key, 0))
except Exception as exc:
    st.error(f"Backend unavailable at {API_BASE}: {exc}")
    st.stop()

tab_sources, tab_runs, tab_ask, tab_briefings = st.tabs(["Sources", "Ingestion Runs", "Ask", "Briefings"])

with tab_sources:
    left, right = st.columns([1, 2])
    with left:
        st.subheader("Add Source")
        source_type = st.selectbox("Type", ["rss", "webpage", "pdf"])
        name = st.text_input("Name")
        if source_type in {"rss", "webpage"}:
            url = st.text_input("URL")
            if st.button("Add Source", type="primary"):
                api_post("/sources", {"source_type": source_type, "name": name or url, "url": url})
                st.rerun()
        else:
            local_path = st.text_input("Local PDF path")
            uploaded = st.file_uploader("Or upload PDF", type=["pdf"])
            if uploaded and st.button("Upload PDF", type="primary"):
                files = {"file": (uploaded.name, uploaded.getvalue(), "application/pdf")}
                response = requests.post(f"{API_BASE}/upload-pdf", params={"name": name or uploaded.name}, files=files, timeout=60)
                response.raise_for_status()
                st.rerun()
            if local_path and st.button("Add Local PDF"):
                api_post("/sources", {"source_type": "pdf", "name": name or Path(local_path).stem, "local_path": local_path})
                st.rerun()
    with right:
        st.subheader("Source List")
        sources = api_get("/sources")
        st.dataframe(sources, use_container_width=True, hide_index=True)
        source_ids = [source["id"] for source in sources]
        if source_ids:
            selected_source = st.selectbox("Run ingestion for source id", source_ids)
            if st.button("Run Ingestion"):
                run = api_post(f"/sources/{selected_source}/ingest")
                st.success(f"Ingestion {run['status']}: +{run['chunks_inserted']} chunks, {run['duplicates_skipped']} duplicates skipped")
                st.rerun()

with tab_runs:
    st.subheader("Ingestion Logs")
    st.dataframe(api_get("/ingestion-runs"), use_container_width=True, hide_index=True)

with tab_ask:
    query = st.text_area("Question", placeholder="Compare what indexed sources say about vector databases.")
    top_k = st.slider("Top K", 1, 12, 5)
    if st.button("Search", type="primary") and query:
        result = api_post("/search", {"query": query, "top_k": top_k})
        st.markdown(result["answer_markdown"])
        st.dataframe(result["hits"], use_container_width=True, hide_index=True)

with tab_briefings:
    topic = st.text_input("Briefing Topic", placeholder="AI data engineering news")
    briefing_k = st.slider("Briefing Evidence Count", 3, 15, 8)
    if st.button("Generate Briefing", type="primary") and topic:
        briefing = api_post("/briefings", {"topic": topic, "top_k": briefing_k})
        st.markdown(briefing["answer_markdown"])
    st.subheader("Briefing History")
    st.dataframe(api_get("/briefings"), use_container_width=True, hide_index=True)

