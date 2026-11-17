"""Retrieval from free public sources. No API keys, no paid services.

Two source kinds:
- `hn_comments`: Hacker News comments from the public Algolia search API
  (https://hn.algolia.com/api). Comments are people describing their own
  work and problems, so they can carry customer-problem evidence. Each comment
  keeps its own permalink, so every quotation cites the comment it came from.
- `web_page`: a public page the founder listed in the brief, fetched once.

A source that cannot be fetched is recorded as unavailable with the error.
Nothing is ever filled in for it.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlencode

import httpx

HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={id}"
# A generic, honest client name: no personal or project-identifying details.
USER_AGENT = "VentureLab/0.2 (open-source research agent)"
MAX_PAGE_BYTES = 2_000_000
MAX_SOURCE_CHARS = 12_000


@dataclass(frozen=True)
class Segment:
    """A span of the source text that comes from one URL (one comment, or the whole page)."""

    start: int
    end: int
    url: str
    author: str | None = None


@dataclass
class Source:
    kind: str  # "hn_comments" or "web_page"
    url: str  # where it was retrieved from (search URL or page URL)
    title: str
    text: str = ""
    segments: list[Segment] = field(default_factory=list)
    status: str = "available"  # "available", "empty" or "unavailable"
    error: str = ""
    retrieved_at: str = ""

    @property
    def available(self) -> bool:
        return self.status == "available"

    def url_at(self, start: int | None) -> str:
        """The URL of the segment containing an offset (the comment permalink)."""
        if start is not None:
            for seg in self.segments:
                if seg.start <= start < seg.end:
                    return seg.url
        return self.url


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head", "nav", "footer", "form", "iframe"}
    BLOCK = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "section",
             "article", "blockquote", "pre", "table", "header"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in self.SKIP:
            self.skip_depth += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    parser = _TextExtractor()
    parser.feed(markup)
    parser.close()
    text = html.unescape("".join(parser.parts))
    lines = [re.sub(r"[ \t\r\f\v]+", " ", line).strip() for line in text.split("\n")]
    out: list[str] = []
    for line in lines:
        if line or (out and out[-1]):
            out.append(line)
    return "\n".join(out).strip()


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class SourceFetcher:
    def __init__(self, transport: httpx.BaseTransport | None = None, timeout_s: float = 20.0) -> None:
        self._http = httpx.Client(
            timeout=httpx.Timeout(timeout_s, connect=10.0),
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def hn_comments(self, query: str, limit: int = 8) -> Source:
        params = {"query": query, "tags": "comment", "hitsPerPage": limit}
        url = f"{HN_SEARCH_URL}?{urlencode(params)}"
        source = Source(kind="hn_comments", url=url, title=f'Hacker News comments matching "{query}"',
                        retrieved_at=_now())
        try:
            response = self._http.get(url)
            response.raise_for_status()
            hits = response.json().get("hits", [])
        except (httpx.HTTPError, ValueError) as exc:
            source.status, source.error = "unavailable", f"{type(exc).__name__}: {exc}"[:300]
            return source
        parts: list[str] = []
        pos = 0
        for hit in hits:
            body = html_to_text(hit.get("comment_text") or "")
            if not body or not hit.get("objectID"):
                continue
            author = str(hit.get("author") or "unknown")
            story = (hit.get("story_title") or "").strip()
            header = f"Comment by {author}" + (f" on the thread \"{story}\"" if story else "") + ":"
            block = f"{header}\n{body}"
            if pos + len(block) > MAX_SOURCE_CHARS:
                break
            permalink = HN_ITEM_URL.format(id=hit["objectID"])
            source.segments.append(Segment(pos, pos + len(block), permalink, author))
            parts.append(block)
            pos += len(block) + 2
        source.text = "\n\n".join(parts)
        if not source.segments:
            source.status, source.error = "empty", "no comments matched the query"
        return source

    def web_page(self, url: str) -> Source:
        source = Source(kind="web_page", url=url, title=url, retrieved_at=_now())
        try:
            response = self._http.get(url)
            response.raise_for_status()
            if len(response.content) > MAX_PAGE_BYTES:
                raise ValueError("page larger than 2 MB")
            kind = response.headers.get("content-type", "")
            if "html" in kind:
                text = html_to_text(response.text)
                title = re.search(r"<title[^>]*>(.*?)</title>", response.text, re.IGNORECASE | re.DOTALL)
                if title:
                    source.title = html.unescape(re.sub(r"\s+", " ", title.group(1))).strip()[:150] or url
            elif kind.startswith("text/plain"):
                text = response.text
            else:
                raise ValueError(f"unsupported content type {kind!r}")
        except (httpx.HTTPError, ValueError) as exc:
            source.status, source.error = "unavailable", f"{type(exc).__name__}: {exc}"[:300]
            return source
        source.text = text[:MAX_SOURCE_CHARS]
        source.segments = [Segment(0, len(source.text), url)]
        if not source.text.strip():
            source.status, source.error = "empty", "page has no readable text"
        return source


def combine(title: str, url: str, picked: list[tuple[Source, Segment]]) -> Source:
    """One source made of selected segments (comments) from several retrieved sources.

    Each segment's text is copied exactly from the source it was retrieved in and
    keeps its own URL, so quotations still cite the comment they come from.
    """
    combined = Source(kind="hn_comments", url=url, title=title, retrieved_at=_now())
    parts: list[str] = []
    pos = 0
    for src, seg in picked:
        block = src.text[seg.start:seg.end]
        combined.segments.append(Segment(pos, pos + len(block), seg.url, seg.author))
        parts.append(block)
        pos += len(block) + 2
    combined.text = "\n\n".join(parts)
    if not combined.segments:
        combined.status, combined.error = "empty", "no retrieved comment was relevant to the brief"
    return combined
