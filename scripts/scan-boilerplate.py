#!/usr/bin/env python3
"""Scan Methodology sections for boilerplate similarity.

Usage:
    python scripts/scan-boilerplate.py              # full report
    python scripts/scan-boilerplate.py --json       # machine-readable
    python scripts/scan-boilerplate.py --tier safe  # only "safe to delete" (>85%)
"""

import argparse
import json
import re
from difflib import SequenceMatcher

from _shared.discovery import discover_agents

REFERENCE = """### Decision Matrix: Methodology Selection by Scenario

| Scenario | Condition | Recommended Approach | Rationale |
|---|---|---|---|
| High-complexity engagement | Multiple interacting constraints, > 3 stakeholders | Structured framework per ISO 31000 | Ensures systematic coverage of cross-cutting concerns |
| Time-sensitive situation | Decision required in < 24 hours, limited data available | Heuristic-driven rapid assessment with explicit assumptions | Speed beats precision when delay increases risk |
| Novel problem space | No established playbook, unfamiliar domain dynamics | First-principles reasoning with lightweight prototyping | Avoids anchoring bias from misapplied analogous cases |
| Cross-functional initiative | Multiple domain experts, conflicting priorities | Multi-criteria decision analysis (MCDA) with weighted scoring | Surfaces hidden trade-offs, reduces political deadlock |
| High-stakes decision | Reversible vs irreversible consequences differ significantly | Pre-mortem analysis + red-team challenge | Surfaces blind spots before commitment, not after"""

SECTION_RE = re.compile(
    r"##\s+.*?(?:Methodology|Decision\s+Framework|Decision\s+Matrix).*?\n(.*?)(?=\n##\s|\Z)",
    re.DOTALL | re.IGNORECASE,
)


def extract_section(body: str) -> str | None:
    m = SECTION_RE.search(body)
    return m.group(1).strip() if m else None


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan Methodology sections for boilerplate")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--tier", choices=["safe", "review", "adapted"])
    args = parser.parse_args()

    agents = list(discover_agents())
    results: list[dict] = []
    no_section = 0

    for _cat, rel_path, filepath in agents:
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        body = content.split("---", 2)[-1] if content.startswith("---") else content
        section = extract_section(body)
        if not section:
            no_section += 1
            continue
        sim = similarity(section, REFERENCE)
        tier = "safe" if sim >= 0.85 else "review" if sim >= 0.50 else "adapted"
        results.append({"path": rel_path, "similarity": round(sim, 3), "tier": tier})

    results.sort(key=lambda x: x["similarity"])

    tiers = {"safe": sum(1 for r in results if r["tier"] == "safe"),
             "review": sum(1 for r in results if r["tier"] == "review"),
             "adapted": sum(1 for r in results if r["tier"] == "adapted")}

    if args.json:
        print(json.dumps({"total": len(agents), "no_section": no_section, "tiers": tiers, "results": results}, indent=2))
        return

    show = [r for r in results if r["tier"] == args.tier] if args.tier else results

    print(f"Boilerplate Scan: {len(agents)} agents")
    print(f"  No Methodology section:  {no_section}")
    print(f"  Safe to delete (>85%):   {tiers['safe']}")
    print(f"  Needs review (50-85%):   {tiers['review']}")
    print(f"  Already adapted (<50%):  {tiers['adapted']}")

    if args.tier:
        print(f"\n--- Tier: {args.tier} ({len(show)} agents) ---")
    for r in show[:30]:
        print(f"  {r['similarity']:.0%}  {r['path']}")
    if len(show) > 30:
        print(f"  ... and {len(show) - 30} more")


if __name__ == "__main__":
    main()
