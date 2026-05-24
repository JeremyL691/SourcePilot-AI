from __future__ import annotations

from html.parser import HTMLParser
from urllib.request import Request, urlopen

from app.config import settings
from app.ingestion.base import ExtractedDocument
from app.ingestion.chunking import clean_text


def fetch_html(url: str) -> str:
    try:
        import requests

        response = requests.get(url, timeout=settings.http_timeout, headers={"User-Agent": settings.user_agent})
        response.raise_for_status()
        response.encoding = response.encoding or "utf-8"
        return response.text
    except ImportError:
        request = Request(url, headers={"User-Agent": settings.user_agent})
        with urlopen(request, timeout=settings.http_timeout) as response:
            return response.read().decode("utf-8", errors="replace")


def extract_webpage(html: str, url: str | None = None) -> ExtractedDocument:
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "svg", "noscript", "nav", "footer", "header", "aside"]):
            tag.decompose()
        title = clean_text(soup.title.get_text(" ", strip=True) if soup.title else "Webpage")
        container = soup.find("main") or soup.find("article") or soup.body or soup
        text = clean_text(container.get_text(" ", strip=True))
    except ImportError:
        parser = _FallbackHTMLTextParser()
        parser.feed(html)
        title = parser.title or "Webpage"
        text = clean_text(" ".join(parser.text_parts))

    return ExtractedDocument(
        title=title or url or "Webpage",
        raw_text=text,
        clean_text=clean_text(text),
        url=url,
        metadata={"source_kind": "webpage"},
    )


def fetch_webpage_text(url: str) -> tuple[str, str]:
    doc = extract_webpage(fetch_html(url), url=url)
    return doc.title, doc.clean_text


def ingest_webpage(url: str) -> list[ExtractedDocument]:
    return [extract_webpage(fetch_html(url), url=url)]


class _FallbackHTMLTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.title: str | None = None
        self._in_title = False
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "title":
            self._in_title = True
        if tag in {"script", "style", "svg", "noscript", "nav", "footer", "header", "aside"}:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "svg", "noscript", "nav", "footer", "header", "aside"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        text = clean_text(data)
        if not text:
            return
        if self._in_title:
            self.title = text
        elif not self._skip_depth:
            self.text_parts.append(text)

