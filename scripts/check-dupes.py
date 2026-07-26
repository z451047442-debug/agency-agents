#!/usr/bin/env python3
"""Detect near-duplicate agents by name and description similarity.

Reads AGENTS.json and uses difflib to compute string similarity
ratios between all agent pairs.  Flags pairs above the similarity
threshold as potential duplicates that merit manual review.

When duplicates are found, compares quality scores to recommend
which agent to keep (higher score = better candidate to retain).
"""

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "AGENTS.json"
RISK_ORDER = {"critical": 0, "high": 1, "general": 2}


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

    # Load scoring to compare duplicates
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "score_agents", str(REPO / "scripts" / "score-agents.py"))
        if spec is None or spec.loader is None:
            raise ImportError("Could not load score_agents module")
        score_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(score_mod)
        has_scorer = True
    except (ImportError, OSError):
        has_scorer = False

    def _get_score(agent_dict):
        if not has_scorer:
            return None
        try:
            f = REPO / agent_dict["path"]
            if f.exists():
                r = score_mod.score_agent(f, check_freshness=False)
                return r["total"], r["grade"], r.get("risk_tier", "general")
        except (ImportError, OSError, KeyError):
            pass
        return None

    print(f"Potential duplicate agents (threshold={args.threshold}):\n")
    for comp, nr, dr, a, b in pairs:
        print(f"  [{comp:.0%}]  {a['name']}  <->  {b['name']}")
        print(f"            name={nr:.0%}  desc={dr:.0%}")
        print(f"            {a['category']}/{a['id']}")
        print(f"            {b['category']}/{b['id']}")

        # Score comparison
        sa = _get_score(a)
        sb = _get_score(b)
        if sa and sb:
            better = a if sa[0] > sb[0] else b if sb[0] > sa[0] else None
            print(f"            scores: {sa[0]}/10 {sa[1]} vs {sb[0]}/10 {sb[1]}")
            if better:
                risk_a = RISK_ORDER.get(sa[2], 99)
                risk_b = RISK_ORDER.get(sb[2], 99)
                if risk_a < risk_b:
                    print(f"            KEEP {a['id']} (higher risk tier: {sa[2]} vs {sb[2]})")
                elif risk_b < risk_a:
                    print(f"            KEEP {b['id']} (higher risk tier: {sb[2]} vs {sa[2]})")
                else:
                    print(f"            KEEP {better['id']} (higher score: {max(sa[0], sb[0])}/10)")
        print()

    print(f"Total: {len(pairs)} pair(s) flagged for review.")
    sys.exit(1)


if __name__ == "__main__":
    main()
