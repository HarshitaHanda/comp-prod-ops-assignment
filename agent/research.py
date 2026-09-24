from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .composio_enrichment import load_composio_catalog, match_toolkit
from .crawler import crawl_official_docs, pages_as_context
from .llm import research_from_context


ROOT = Path(__file__).resolve().parents[1]
APPS_PATH = ROOT / "data" / "apps.json"
RESULTS_PATH = ROOT / "data" / "results.json"


def run(limit: int | None = None, start: int = 1) -> list[dict]:
    load_dotenv(ROOT / ".env")
    apps = json.loads(APPS_PATH.read_text(encoding="utf-8"))
    existing = {
        item["id"]: item
        for item in json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    }

    selected = [a for a in apps if a["id"] >= start]
    if limit is not None:
        selected = selected[:limit]

    try:
        catalog = load_composio_catalog()
    except Exception as exc:
        print(f"[warn] Composio catalog enrichment unavailable: {exc}")
        catalog = []

    for idx, app in enumerate(selected, start=1):
        print(f"[{idx}/{len(selected)}] Researching {app['name']}...")
        pages = crawl_official_docs(app["hint_url"])
        if not pages:
            row = {**app, **existing.get(app["id"], {}), "status": "needs-human"}
            row["research_note"] = "Could not retrieve usable official source text."
            existing[app["id"]] = row
            continue

        try:
            finding = research_from_context(app, pages_as_context(pages)).model_dump()
        except Exception as exc:
            row = {**app, **existing.get(app["id"], {}), "status": "needs-human"}
            row["research_note"] = f"LLM extraction failed: {type(exc).__name__}"
            existing[app["id"]] = row
            continue

        row = {
            **app,
            **finding,
            "status": "researched",
            "composio_toolkit": match_toolkit(app["name"], catalog) if catalog else None,
            "researched_at": datetime.now(timezone.utc).isoformat(),
        }
        existing[app["id"]] = row

        RESULTS_PATH.write_text(
            json.dumps(
                [existing[a["id"]] for a in apps if a["id"] in existing],
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    return [existing[a["id"]] for a in apps if a["id"] in existing]


def main() -> None:
    parser = argparse.ArgumentParser(description="Research the 100-app integration set.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--start", type=int, default=1)
    args = parser.parse_args()
    run(limit=args.limit, start=args.start)


if __name__ == "__main__":
    main()
