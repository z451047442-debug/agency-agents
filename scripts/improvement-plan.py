#!/usr/bin/env python3
"""Generate actionable improvement plans from v5 scoring results.

Runs v5 scoring and outputs per-agent improvement instructions for every
agent scoring below A-grade. Each plan entry maps a low-scoring dimension
to a concrete action with estimated score gain.

Usage:
    python scripts/improvement-plan.py                    # all agents below A
    python scripts/improvement-plan.py --category aerospace
    python scripts/improvement-plan.py --agent administration-procurement
    python scripts/improvement-plan.py --json              # machine-readable output
    python scripts/improvement-plan.py --below B           # filter by v5 grade
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(
        description="Generate v5 improvement plans for agents below A-grade")
    parser.add_argument("--category", "-c",
                        help="Filter by category directory")
    parser.add_argument("--agent",
                        help="Show plan for a single agent (by ID)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--v6", action="store_true",
                        help="Use v6 scoring (0-16 scale)")
    parser.add_argument("--below", default="A", choices=["A", "B", "C"],
                        help="Show agents below this grade (default: A = all non-A)")
    args = parser.parse_args()

    # Run scoring (v6 or v5)
    score_flag = "--v6" if args.v6 else "--v5"
    score_key = "v6" if args.v6 else "v5"
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/score-agents.py"),
         score_flag, "--json", "--no-freshness"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    if result.returncode != 0:
        print(f"ERROR: scoring failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    if score_key not in data:
        print(f"ERROR: {score_key} scoring data not found in output", file=sys.stderr)
        sys.exit(1)

    agents = data[score_key]["agents"]

    # Filter
    if args.agent:
        agents = [a for a in agents if a["id"] == args.agent]
        if not agents:
            print(f"ERROR: agent '{args.agent}' not found", file=sys.stderr)
            sys.exit(1)
    if args.category:
        agents = [a for a in agents if a["category"] == args.category]

    # Filter by grade threshold
    grade_field = "v6_grade" if args.v6 else "v5_grade"
    total_field = "v6_total" if args.v6 else "v5_total"
    grade_order = {"D": 0, "C": 1, "B": 2, "A": 3}
    cutoff = grade_order[args.below]
    agents = [a for a in agents if grade_order.get(a[grade_field], 0) < cutoff]

    if not agents:
        print("No agents match the filter criteria.")
        sys.exit(0)

    # Sort by score ascending (worst first)
    agents.sort(key=lambda a: a[total_field])

    if args.json:
        output = {
            "generated": data["generated"],
            "total_agents": len(agents),
            "grade_distribution": {},
            "agents": [],
        }
        grades = defaultdict(int)
        for a in agents:
            grades[a[grade_field]] += 1
            output["agents"].append({
                "id": a["id"],
                "category": a["category"],
                "total": a[total_field],
                "grade": a[grade_field],
                "improvement_plan": a.get(f"{score_key}_improvement_plan", []),
            })
        output["grade_distribution"] = dict(grades)
        json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    # Human-readable output
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    RESET = "\033[0m"

    print(f"\n{BOLD}=== {score_key} Improvement Plans ==={RESET}")
    print(f"Agents below {args.below}-grade: {len(agents)}")
    print()

    for a in agents:
        grade = a[grade_field]
        color = {"A": GREEN, "B": CYAN, "C": YELLOW, "D": RED}.get(grade, RESET)
        print(f"{color}{a[total_field]:4.1f} {grade} {a['id']}{RESET}  ({a['category']})")

        plan = a.get(f"{score_key}_improvement_plan", [])
        if not plan:
            print(f"  {GREEN}No improvements needed — all dimensions at max{RESET}")
            continue

        for item in plan[:5]:
            dim = item["dim"]
            gap = item["gap"]
            print(f"  {YELLOW}+{gap:.1f}{RESET} {dim}: {item['action']}")

        scores = a.get(f"{score_key}_scores", {})
        dims_str = "  ".join(f"{k}={v}" for k, v in scores.items())
        print(f"  {RESET}[{dims_str}]{RESET}")
        print()


if __name__ == "__main__":
    main()
