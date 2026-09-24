from __future__ import annotations

import os
import re
from collections import deque
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = int(os.getenv("RESEARCH_TIMEOUT_SECONDS", "20"))
DEFAULT_MAX_PAGES = int(os.getenv("RESEARCH_MAX_PAGES", "5"))

LIKELY_DOC_WORDS = (
    "api", "developer", "developers", "auth", "oauth", "token", "webhook",
    "integration", "mcp", "docs", "reference", "graphql", "rest",
)

USER_AGENT = (
    "Mozilla/5.0 (compatible; ComposioProductOpsResearch/1.0; "
    "+https://github.com/HarshitaHanda/comp-prod-ops-assignment)"
)


@dataclass
class Page:
    url: str
    title: str
    text: str


def _registrable_hint(hostname: str) -> str:
    parts = (hostname or "").lower().split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else hostname.lower()


def _is_official(seed_url: str, candidate_url: str) -> bool:
    seed = _registrable_hint(urlparse(seed_url).hostname or "")
    candidate = _registrable_hint(urlparse(candidate_url).hostname or "")
    return bool(seed and candidate and seed == candidate)


def _clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    return re.sub(r"\s+", " ", text).strip()


def _score_link(url: str, label: str) -> int:
    haystack = f"{url} {label}".lower()
    return sum(1 for word in LIKELY_DOC_WORDS if word in haystack)


def crawl_official_docs(seed_url: str, max_pages: int = DEFAULT_MAX_PAGES) -> list[Page]:
    if not seed_url:
        return []

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    queue: deque[str] = deque([seed_url.replace("http://", "https://", 1)])
    visited: set[str] = set()
    pages: list[Page] = []

    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            response = session.get(url, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
            response.raise_for_status()
        except requests.RequestException:
            continue

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type and "text/plain" not in content_type:
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        text = _clean_text(soup)
        if text:
            pages.append(Page(url=response.url, title=title, text=text[:45_000]))

        candidates: list[tuple[int, str]] = []
        for a in soup.find_all("a", href=True):
            absolute = urljoin(response.url, a["href"]).split("#")[0]
            if absolute in visited or not absolute.startswith(("http://", "https://")):
                continue
            if not _is_official(seed_url, absolute):
                continue
            score = _score_link(absolute, a.get_text(" ", strip=True))
            if score:
                candidates.append((score, absolute))

        for _, candidate in sorted(candidates, reverse=True)[:12]:
            if candidate not in visited:
                queue.append(candidate)

    return pages


def pages_as_context(pages: list[Page]) -> str:
    blocks = []
    for i, page in enumerate(pages, start=1):
        blocks.append(
            f"SOURCE {i}\nURL: {page.url}\nTITLE: {page.title}\nTEXT:\n{page.text}"
        )
    return "\n\n---\n\n".join(blocks)
