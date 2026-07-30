#!/usr/bin/env python3
"""NEXUS phase coverage visualization — agent count, category diversity, and gaps.

Usage:
    python scripts/nexus-coverage.py                          # full coverage
    python scripts/nexus-coverage.py --category engineering   # single category
    python scripts/nexus-coverage.py --gaps                   # gaps only
    python scripts/nexus-coverage.py --json                   # machine output
"""

import argparse
import json
import sys
from pathlib import Path

from _shared.discovery import discover_agents
from _shared.frontmatter import get_frontmatter_text, get_list_field
from _shared import BOLD, CYAN, GREEN, RED, RESET, YELLOW

PHASE_LABELS: dict[str, str] = {
    "phase-0-discovery": "Discovery",
    "phase-1-strategy": "Strategy",
    "phase-2-foundation": "Foundation",
    "phase-3-build": "Build",
    "phase-4-hardening": "Hardening",
    "phase-5-launch": "Launch",
    "phase-6-operate": "Operate",
}

PHASE_ORDER = [
    "phase-0-discovery",
    "phase-1-strategy",
    "phase-2-foundation",
    "phase-3-build",
    "phase-4-hardening",
    "phase-5-launch",
    "phase-6-operate",
]

GAP_AGENT_THRESHOLD = 100       # flag phases with fewer than this many agents
GAP_CATEGORY_THRESHOLD = 10     # flag phases with fewer than this many categories


def collect_phase_data(category_filter: str | None = None) -> dict[str, dict]:
    """Collect NEXUS phase data across all agents.

    Returns a dict keyed by phase ID, where each value has:
        agent_count: int
        agents: list[str]
        categories: set[str]
    """
    phases: dict[str, dict] = {
        pid: {"agent_count": 0, "agents": [], "categories": set()}
        for pid in PHASE_ORDER
    }

    for cat, _rel_path, file_path in discover_agents(category_filter):
        try:
            content = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not content.startswith("---"):
            continue

        fm_text = get_frontmatter_text(content)
        roles = get_list_field("nexus_roles", fm_text)

        if not roles:
            continue

        for role in roles:
            if role in phases:
                phases[role]["agent_count"] += 1
                phases[role]["agents"].append(file_path.stem)
                phases[role]["categories"].add(cat)

    return phases


def compute_coverage_scores(phases: dict[str, dict]) -> dict[str, float]:
    """Compute a coverage score (0.0 - 1.0) for each phase.

    Score = 0.5 * (agent_count / max_count) + 0.5 * (category_count / total_categories)
    """
    max_count = max(p["agent_count"] for p in phases.values()) if phases else 1
    if max_count == 0:
        max_count = 1

    all_categories: set[str] = set()
    for p in phases.values():
        all_categories.update(p["categories"])
    total_cats = len(all_categories) if all_categories else 1

    scores: dict[str, float] = {}
    for pid, data in phases.items():
        agent_norm = data["agent_count"] / max_count
        cat_norm = len(data["categories"]) / total_cats
        scores[pid] = round(0.5 * agent_norm + 0.5 * cat_norm, 2)

    return scores


def find_gaps(phases: dict[str, dict]) -> list[dict]:
    """Identify phases with low coverage (gaps).

    Returns a list of gap entries sorted by severity.
    """
    gaps: list[dict] = []
    for pid in PHASE_ORDER:
        data = phases[pid]
        issues: list[str] = []
        if data["agent_count"] < GAP_AGENT_THRESHOLD:
            issues.append(
                f"low agent count ({data['agent_count']} < {GAP_AGENT_THRESHOLD})"
            )
        cat_count = len(data["categories"])
        if cat_count < GAP_CATEGORY_THRESHOLD:
            issues.append(
                f"low category diversity ({cat_count} < {GAP_CATEGORY_THRESHOLD})"
            )
        if issues:
            gaps.append({
                "phase": pid,
                "label": PHASE_LABELS[pid],
                "agent_count": data["agent_count"],
                "categories": cat_count,
                "issues": issues,
                "severity": len(issues),
            })

    gaps.sort(key=lambda g: (-g["severity"], g["agent_count"]))
    return gaps


def print_text_report(
    phases: dict[str, dict],
    scores: dict[str, float],
    gaps: list[dict] | None = None,
    category_filter: str | None = None,
) -> None:
    """Print a human-readable NEXUS coverage report."""
    max_count = max(p["agent_count"] for p in phases.values()) if phases else 0
    bar_max = 20  # max bar width in characters

    title = "NEXUS Phase Coverage"
    if category_filter:
        title += f" — {category_filter}"

    print()
    print(f"{BOLD}{title}{RESET}")
    print(f"{'=' * 50}")

    for pid in PHASE_ORDER:
        data = phases[pid]
        count = data["agent_count"]
        cat_count = len(data["categories"])
        score = scores.get(pid, 0.0)

        # Build bar
        bar_len = int((count / max_count) * bar_max) if max_count > 0 else 0
        bar = "█" * bar_len

        # Flag colour for gaps
        is_gap = gaps is not None and any(g["phase"] == pid for g in gaps)
        colour = YELLOW if is_gap else CYAN

        # Score colour
        if score >= 0.7:
            score_colour = GREEN
        elif score >= 0.4:
            score_colour = YELLOW
        else:
            score_colour = RED

        print(
            f"  {colour}{pid:<22}{RESET} {bar:<{bar_max}}  "
            f"{BOLD}{count:<5}{RESET} agents  "
            f"{cat_count:<3} categories  "
            f"{score_colour}score: {score:.2f}{RESET}"
        )

    total_agents = sum(p["agent_count"] for p in phases.values())
    total_cats_all: set[str] = set()
    for p in phases.values():
        total_cats_all.update(p["categories"])
    print(f"\n  Total agents with nexus_roles: {total_agents}")
    print(f"  Total categories represented:  {len(total_cats_all)}")

    # Print gaps section
    if gaps is not None and gaps:
        print(f"\n{RED}{BOLD}Coverage Gaps{RESET}")
        print(f"{'=' * 50}")
        for g in gaps:
            issues_str = "; ".join(g["issues"])
            print(
                f"  {YELLOW}{g['phase']}{RESET} ({g['label']}) — {issues_str}"
            )
        print()


def print_json_report(
    phases: dict[str, dict],
    scores: dict[str, float],
    gaps: list[dict] | None = None,
) -> None:
    """Print machine-readable JSON output."""
    output: dict = {
        "phases": {},
        "scores": scores,
        "summary": {
            "total_agents": sum(p["agent_count"] for p in phases.values()),
            "total_categories": len({
                cat for p in phases.values() for cat in p["categories"]
            }),
        },
    }

    for pid in PHASE_ORDER:
        data = phases[pid]
        output["phases"][pid] = {
            "label": PHASE_LABELS[pid],
            "agent_count": data["agent_count"],
            "categories": sorted(data["categories"]),
            "category_count": len(data["categories"]),
        }

    if gaps is not None:
        output["gaps"] = gaps

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize NEXUS phase coverage across all agents"
    )
    parser.add_argument(
        "--category", "-c",
        help="Drill into a single category (e.g., engineering)",
    )
    parser.add_argument(
        "--gaps", action="store_true",
        help="Only show coverage gaps (phases below thresholds)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output machine-readable JSON",
    )
    args = parser.parse_args()

    phases = collect_phase_data(args.category)
    scores = compute_coverage_scores(phases)
    gaps = find_gaps(phases)

    if args.json:
        print_json_report(phases, scores, gaps)
        return

    print_text_report(
        phases, scores,
        gaps=gaps if args.gaps else None,
        category_filter=args.category,
    )


if __name__ == "__main__":
    main()
