from __future__ import annotations

from dataclasses import dataclass

from playwright.sync_api import sync_playwright


@dataclass
class BrowserPage:
    url: str
    title: str
    text: str


def render_pages(urls: list[str], max_pages: int = 4) -> list[BrowserPage]:
    """Render evidence pages in Chromium for a verification pass.

    This intentionally uses a different retrieval path from the requests-based first
    pass, so JS-rendered documentation can expose claims the first pass missed.
    """
    pages: list[BrowserPage] = []
    unique_urls = list(dict.fromkeys(urls))[:max_pages]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (compatible; ComposioProductOpsResearch/1.0; "
                "+https://github.com/HarshitaHanda/comp-prod-ops-assignment)"
            )
        )
        for url in unique_urls:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(800)
                pages.append(
                    BrowserPage(
                        url=page.url,
                        title=page.title(),
                        text=page.locator("body").inner_text(timeout=10_000)[:50_000],
                    )
                )
            except Exception:
                continue
        browser.close()

    return pages


def browser_pages_as_context(pages: list[BrowserPage]) -> str:
    return "\n\n---\n\n".join(
        f"SOURCE {i}\nURL: {page.url}\nTITLE: {page.title}\nTEXT:\n{page.text}"
        for i, page in enumerate(pages, start=1)
    )
