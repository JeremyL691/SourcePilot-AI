from __future__ import annotations

import email.utils
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

from app.config import settings
from app.ingestion.base import ExtractedDocument
from app.ingestion.chunking import clean_text
from app.ingestion.webpage import fetch_webpage_text


def fetch_url_bytes(url: str) -> bytes:
    try:
        import requests

        response = requests.get(url, timeout=settings.http_timeout, headers={"User-Agent": settings.user_agent})
        response.raise_for_status()
        return response.content
    except ImportError:
        request = Request(url, headers={"User-Agent": settings.user_agent})
        with urlopen(request, timeout=settings.http_timeout) as response:
            return response.read()


def _entry_text(entry: dict) -> str:
    fields = [
        entry.get("summary"),
        entry.get("description"),
        entry.get("content"),
    ]
    content = fields[-1]
    if isinstance(content, list) and content:
        fields[-1] = content[0].get("value")
    return clean_text(" ".join(str(field or "") for field in fields))


def parse_rss_bytes(payload: bytes, fetch_full_articles: bool = False) -> list[ExtractedDocument]:
    try:
        import feedparser

        parsed = feedparser.parse(payload)
        docs: list[ExtractedDocument] = []
        for entry in parsed.entries:
            title = clean_text(entry.get("title", "Untitled RSS entry"))
            link = entry.get("link")
            body = _entry_text(entry)
            if fetch_full_articles and link:
                try:
                    article_title, article_text = fetch_webpage_text(link)
                    body = article_text or body
                    title = article_title or title
                except Exception as exc:
                    body = body or f"Full article fetch failed, but the RSS item was preserved. Error: {exc}"
            if not title and not body:
                continue
            docs.append(
                ExtractedDocument(
                    title=title or link or "Untitled RSS entry",
                    raw_text=body,
                    clean_text=clean_text(body),
                    url=link,
                    author=entry.get("author"),
                    published_at=entry.get("published") or _published_from_struct(entry),
                    metadata={"source_kind": "rss"},
                )
            )
        return docs
    except ImportError:
        return _parse_rss_with_elementtree(payload)


def _published_from_struct(entry) -> str | None:
    parsed = entry.get("published_parsed")
    if not parsed:
        return None
    return email.utils.formatdate(email.utils.mktime_tz(parsed + (0,)), usegmt=True)


def _parse_rss_with_elementtree(payload: bytes) -> list[ExtractedDocument]:
    root = ET.fromstring(payload)
    docs: list[ExtractedDocument] = []
    for item in root.findall(".//item"):
        title = clean_text(item.findtext("title") or "Untitled RSS entry")
        link = clean_text(item.findtext("link") or "")
        raw_text = clean_text(" ".join([item.findtext("description") or "", item.findtext("summary") or ""]))
        if not title and not raw_text:
            continue
        docs.append(
            ExtractedDocument(
                title=title or link or "Untitled RSS entry",
                raw_text=raw_text,
                clean_text=clean_text(raw_text),
                url=link or None,
                published_at=item.findtext("pubDate"),
                metadata={"source_kind": "rss"},
            )
        )
    return docs


def ingest_rss(url: str, fetch_full_articles: bool = False) -> list[ExtractedDocument]:
    return parse_rss_bytes(fetch_url_bytes(url), fetch_full_articles=fetch_full_articles)
