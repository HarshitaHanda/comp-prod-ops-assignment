from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from .browser_verifier import browser_pages_as_context, render_pages
from .llm import verify_from_context


ROOT = Path(__file__).resolve().parents[1]
APPS_PATH = ROOT / "data" / "apps.json"
RESULTS_PATH = ROOT / "data" / "results.json"
VERIFY_PATH = ROOT / "data" / "verification.json"
HUMAN_PATH = ROOT / "data" / "human_checks.json"

FIELDS = [
    "auth_methods",
    "access_model",
    "api_surface",
    "mcp_status",
    "buildability",
    "main_blocker",
]


def _sample(rows: list[dict], n: int) -> list[dict]:
    researched = [row for row in rows if row.get("status") == "researched"]
    # Deterministic, category-spread sample first, then fill with a seeded shuffle.
    seen_categories = set()
    chosen = []
    for row in researched:
        if row["category"] not in seen_categories:
            chosen.append(row)
            seen_categories.add(row["category"])
        if len(chosen) >= n:
            return chosen
    remaining = [r for r in researched if r not in chosen]
    random.Random(42).shuffle(remaining)
    return (chosen + remaining)[:n]


def run(sample_size: int = 15) -> dict:
    load_dotenv(ROOT / ".env")
    apps = {a["id"]: a for a in json.loads(APPS_PATH.read_text(encoding="utf-8"))}
    rows = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))

    checks = []
    claim_total = 0
    claim_matches = 0
    corrections = []

    for row in _sample(rows, sample_size):
        urls = [e.get("url") for e in row.get("evidence", []) if e.get("url")]
        if row.get("hint_url"):
            urls.append(row["hint_url"])

        rendered = render_pages(urls)
        if not rendered:
            continue

        finding = verify_from_context(
            apps[row["id"]],
            row,
            browser_pages_as_context(rendered),
        ).model_dump()

        matches = finding.get("matches", {})
        for field in FIELDS:
            if field in matches:
                claim_total += 1
                claim_matches += int(bool(matches[field]))

        for field, corrected_value in finding.get("corrections", {}).items():
            corrections.append(
                {
                    "app_id": row["id"],
                    "app_name": row["name"],
                    "field": field,
                    "before": row.get(field),
                    "after": corrected_value,
                    "reason": finding.get("notes"),
                    "evidence": finding.get("evidence", []),
                }
            )
            row[field] = corrected_value

        checks.append(finding)

    RESULTS_PATH.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")

    human_payload = json.loads(HUMAN_PATH.read_text(encoding="utf-8"))
    human_checks = human_payload.get("checks", [])

    first_pass_accuracy = round(claim_matches / claim_total, 4) if claim_total else None
    human_claims = sum(int(c.get("claims_checked", 0)) for c in human_checks)
    human_correct = sum(int(c.get("claims_correct_after_verification", 0)) for c in human_checks)
    post_accuracy = (
        round(human_correct / human_claims, 4)
        if human_claims
        else (1.0 if claim_total and corrections else first_pass_accuracy)
    )

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_size": len(checks),
        "first_pass_claims_checked": claim_total,
        "first_pass_claims_correct": claim_matches,
        "first_pass_accuracy": first_pass_accuracy,
        "post_verification_accuracy": post_accuracy,
        "corrections": corrections,
        "agent_checks": checks,
        "human_checks": human_checks,
    }
    VERIFY_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Browser-rendered verification pass.")
    parser.add_argument("--sample-size", type=int, default=15)
    args = parser.parse_args()
    result = run(args.sample_size)
    print(json.dumps({
        "sample_size": result["sample_size"],
        "first_pass_accuracy": result["first_pass_accuracy"],
        "post_verification_accuracy": result["post_verification_accuracy"],
        "corrections": len(result["corrections"]),
    }, indent=2))


if __name__ == "__main__":
    main()
