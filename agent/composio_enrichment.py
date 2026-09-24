from __future__ import annotations

import re
from typing import Any

from composio import Composio


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return vars(value)


def _items_and_cursor(response: Any) -> tuple[list[dict], str | None]:
    data = _as_dict(response)
    raw_items = (
        data.get("items")
        or data.get("toolkits")
        or data.get("data")
        or []
    )
    items = [_as_dict(item) for item in raw_items]
    cursor = (
        data.get("next_cursor")
        or data.get("nextCursor")
        or data.get("cursor")
    )
    return items, cursor


def load_composio_catalog() -> list[dict]:
    """Load the project's visible Composio toolkit catalog using the official SDK."""
    composio = Composio()
    catalog: list[dict] = []
    cursor = None

    for _ in range(50):
        response = composio.toolkits.list(
            limit=100,
            cursor=cursor,
            sort_by="alphabetically",
            managed_by="all",
        )
        items, next_cursor = _items_and_cursor(response)
        catalog.extend(items)
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return catalog


def match_toolkit(app_name: str, catalog: list[dict]) -> dict | None:
    target = _norm(app_name)
    aliases = {
        "larklarksuite": ["lark", "larksuite"],
        "whatsappbusiness": ["whatsapp"],
        "salesforcecommercecloud": ["salesforcecommercecloud", "salesforce"],
        "amazon selling partner": ["amazonsellingpartner", "amazonspapi"],
        "mondaycom": ["monday"],
        "mongodb atlas": ["mongodbatlas", "mongodb"],
        "youtube transcript": ["youtubetranscript"],
    }
    candidates = [target, *aliases.get(app_name.lower(), [])]

    best = None
    best_score = 0
    for toolkit in catalog:
        name = str(toolkit.get("name") or "")
        slug = str(toolkit.get("slug") or toolkit.get("id") or "")
        probe = {_norm(name), _norm(slug)}
        for candidate in candidates:
            if not candidate:
                continue
            if candidate in probe:
                score = 3
            elif any(candidate in p or p in candidate for p in probe if p):
                score = 2
            else:
                score = 0
            if score > best_score:
                best = toolkit
                best_score = score

    if best_score < 2 or best is None:
        return None

    return {
        "name": best.get("name"),
        "slug": best.get("slug") or best.get("id"),
        "categories": best.get("categories") or best.get("category"),
    }
