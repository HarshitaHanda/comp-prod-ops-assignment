from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULTS_PATH = ROOT / "data" / "results.json"
SUMMARY_PATH = ROOT / "data" / "summary.json"


def run() -> dict:
    rows = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    researched = [r for r in rows if r.get("status") == "researched"]

    auth = Counter()
    access = Counter()
    build = Counter()
    blockers = Counter()
    by_category = defaultdict(lambda: {"total": 0, "buildable": 0, "gated": 0})

    for row in researched:
        for method in row.get("auth_methods", []):
            auth[method] += 1
        if row.get("access_model"):
            access[row["access_model"]] += 1
        if row.get("buildability"):
            build[row["buildability"]] += 1
        blocker = row.get("main_blocker")
        if blocker:
            blockers[blocker] += 1

        cat = by_category[row["category"]]
        cat["total"] += 1
        cat["buildable"] += int(row.get("buildability") == "yes")
        cat["gated"] += int(row.get("access_model") in {
            "admin-gated", "partner-gated", "contact-sales"
        })

    payload = {
        "researched": len(researched),
        "total": len(rows),
        "auth_methods": auth.most_common(),
        "access_models": access.most_common(),
        "buildability": build.most_common(),
        "top_blockers": blockers.most_common(8),
        "categories": dict(by_category),
    }
    SUMMARY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
