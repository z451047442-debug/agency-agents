#!/usr/bin/env python3
"""Detect near-duplicate agents by name and description similarity.

Reads AGENTS.json and uses difflib to compute string similarity
ratios between all agent pairs.  Flags pairs above the similarity
threshold as potential duplicates that merit manual review.
"""

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "AGENTS.json"


def find_duplicates(
    agents: list[dict],
    threshold: float,
    category_filter: str | None = None,
) -> list[tuple[float, float, float, dict, dict]]:
    """Return duplicate pairs with composite similarity above threshold."""
    if category_filter:
        agents = [a for a in agents if a["category"] == category_filter]

    n = len(agents)
    pairs: list[tuple[float, float, float, dict, dict]] = []

    for i in range(n):
        for j in range(i + 1, n):
            a, b = agents[i], agents[j]

            name_ratio = SequenceMatcher(
                None, a["name"].lower(), b["name"].lower()
            ).ratio()

            desc_ratio = SequenceMatcher(
                None,
                a.get("description", "").lower(),
                b.get("description", "").lower(),
            ).ratio()

            composite = name_ratio * 0.6 + desc_ratio * 0.4

            if composite >= threshold:
                pairs.append((composite, name_ratio, desc_ratio, a, b))

    pairs.sort(key=lambda x: x[0], reverse=True)
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect near-duplicate agents by name and description similarity"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        help="Similarity ratio above which to flag (default: 0.85)",
    )
    parser.add_argument(
        "--category",
        help="Only compare agents in this category",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    if not INDEX_PATH.exists():
        print(f"AGENTS.json not found at {INDEX_PATH}. Run: ./scripts/generate-index.sh")
        sys.exit(1)

    with open(INDEX_PATH, encoding="utf-8") as f:
        data = json.load(f)

    agents = data["agents"]

    if args.category:
        print(f"Category filter: {args.category} ({len([a for a in agents if a['category'] == args.category])} agents)\n")

    pairs = find_duplicates(agents, args.threshold, args.category)

    if args.json:
        result = [
            {
                "composite": round(comp, 4),
                "name_ratio": round(nr, 4),
                "desc_ratio": round(dr, 4),
                "agent_a": a["id"],
                "agent_b": b["id"],
            }
            for comp, nr, dr, a, b in pairs
        ]
        import json as _json
        print(_json.dumps(result, indent=2))
        sys.exit(1 if pairs else 0)

    if not pairs:
        print(f"No duplicate pairs found (threshold={args.threshold}).")
        sys.exit(0)

    print(f"Potential duplicate agents (threshold={args.threshold}):\n")
    for comp, nr, dr, a, b in pairs:
        print(f"  [{comp:.0%}]  {a['name']}  <->  {b['name']}")
        print(f"            name={nr:.0%}  desc={dr:.0%}")
        print(f"            {a['category']}/{a['id']}")
        print(f"            {b['category']}/{b['id']}")
        print()

    print(f"Total: {len(pairs)} pair(s) flagged for review.")
    sys.exit(1)


if __name__ == "__main__":
    main()
