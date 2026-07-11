#!/usr/bin/env python3
"""Suggest NEXUS agent activation for a given phase and mode.

Reads AGENTS.json and outputs a phase-specific activation plan with agent
names, categories, and quality gate criteria.  Does NOT activate agents —
it helps a human operator decide whom to activate.

Usage:
    python scripts/nexus-orchestrator.py --phase 0
    python scripts/nexus-orchestrator.py --phase 3 --mode micro
    python scripts/nexus-orchestrator.py --phase 4 --json
"""

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "AGENTS.json"

PHASE_LABELS = {
    "0": "Discovery",
    "1": "Strategy",
    "2": "Foundation",
    "3": "Build",
    "4": "Hardening",
    "5": "Launch",
    "6": "Operate",
}

PHASE_TO_ROLE = {k: f"phase-{k}-{v.lower()}" for k, v in PHASE_LABELS.items()}

GATE_KEEPERS = {
    "0": ("Executive Summary Generator", "executive-summary-generator"),
    "1": ("Studio Producer + Reality Checker", "studio-producer"),
    "2": ("DevOps Automator + Evidence Collector", "devops-automator"),
    "3": ("Agents Orchestrator", "agents-orchestrator"),
    "4": ("Reality Checker (sole authority)", "testing-reality-checker"),
    "5": ("Studio Producer + Analytics Reporter", "studio-producer"),
    "6": ("Agents Orchestrator (continuous)", "agents-orchestrator"),
}

GATE_CRITERIA = {
    "0": [
        "Market opportunity validated (TAM threshold met)",
        "≥3 validated user pain points",
        "No blocking compliance issues",
        "Technology feasibility confirmed",
    ],
    "1": [
        "Architecture covers all requirements (100% spec coverage)",
        "Brand system complete (logo, colors, typography, voice)",
        "Technical feasibility validated",
        "Sprint plan realistic (velocity-based estimation)",
    ],
    "2": [
        "CI/CD pipeline operational (build + test + deploy)",
        "Database schema deployed (all tables/indexes)",
        "API scaffold responding (health check endpoints)",
        "Frontend rendering (skeleton app loads in browser)",
        "Monitoring active (dashboards showing metrics)",
    ],
    "3": [
        "All sprint tasks pass QA (100% completion)",
        "API endpoints validated (all endpoints tested)",
        "Performance baselines met (P95 < 200ms)",
        "Brand consistency verified (95%+ adherence)",
        "No critical bugs (zero P0/P1 open)",
    ],
    "4": [
        "User journeys complete (all critical paths working)",
        "Cross-device consistency (Desktop + Tablet + Mobile)",
        "Performance certified (P95 < 200ms, LCP < 2.5s)",
        "Security validated (zero critical vulnerabilities)",
        "Specification compliance (100% of requirements)",
    ],
    "5": [
        "Deployment successful (zero-downtime)",
        "Systems stable (no P0/P1 in first 48 hours)",
        "User acquisition active (channels driving traffic)",
        "Feedback loop operational",
    ],
    "6": [
        "SLO compliance maintained",
        "P0 incidents < 1 per month",
        "Quarterly trend analysis completed",
        "Continuous improvement backlog active",
    ],
}

MODE_LIMITS = {"micro": 10, "sprint": 25, "full": 999}


def load_agents() -> list[dict]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)["agents"]


def filter_by_phase(agents: list[dict], phase: str) -> list[dict]:
    role = PHASE_TO_ROLE[phase]
    return [a for a in agents if role in (a.get("nexus_roles") or [])]


def format_text(agents: list[dict], phase: str, mode: str) -> str:
    phase_label = PHASE_LABELS[phase]
    limit = MODE_LIMITS[mode]
    gate_label, _gate_id = GATE_KEEPERS[phase]
    criteria = GATE_CRITERIA[phase]

    # Group by category
    by_cat: dict[str, list[dict]] = {}
    for a in agents:
        cat = a.get("category", "other")
        by_cat.setdefault(cat, []).append(a)

    lines = []
    lines.append(f"NEXUS Phase {phase} — {phase_label} ({mode.title()} Mode)")
    lines.append("=" * 60)

    n_shown = 0
    for cat in sorted(by_cat):
        cat_agents = by_cat[cat]
        if limit < 999:
            # In limited modes, show most relevant categories first
            cat_agents.sort(key=lambda a: len(a.get("nexus_roles") or []), reverse=True)
        lines.append(f"\n  [{cat}]  ({len(cat_agents)} agents)")

        for a in cat_agents:
            if n_shown >= limit:
                break
            name = a.get("name", a["id"])
            lines.append(f"    - {name}")
            n_shown += 1
        if n_shown >= limit:
            remaining = len(agents) - n_shown
            lines.append(f"\n  ... and {remaining} more agents (use --mode full for all)")
            break

    lines.append(f"\n{'─' * 60}")
    lines.append("Quality Gate")
    lines.append(f"  Gate Keeper: {gate_label}")
    lines.append("  Criteria:")
    for c in criteria:
        lines.append(f"    ☐ {c}")

    lines.append(f"\n{'─' * 60}")
    lines.append(f"Total: {len(agents)} agents available for Phase {phase}")
    lines.append(f"Shown: {min(n_shown, len(agents))}")
    lines.append("")
    lines.append(
        "To activate: copy the agent names above and invoke them in your AI tool."
    )
    label_lower = PHASE_LABELS[phase].lower()
    lines.append(
        f"See docs/playbooks/phase-{phase}-{label_lower}.md for detailed activation prompts."
    )

    return "\n".join(lines)


def format_json(agents: list[dict], phase: str) -> str:
    return json.dumps(
        {
            "phase": phase,
            "label": PHASE_LABELS[phase],
            "gate_keeper": GATE_KEEPERS[phase][0],
            "criteria": GATE_CRITERIA[phase],
            "agent_count": len(agents),
            "agents": [
                {"id": a["id"], "name": a["name"], "category": a["category"]}
                for a in agents
            ],
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK workaround

    parser = argparse.ArgumentParser(
        description="Suggest NEXUS agent activation for a given phase"
    )
    parser.add_argument(
        "--phase", "-p", required=True, choices=["0", "1", "2", "3", "4", "5", "6"],
        help="NEXUS phase (0-6)",
    )
    parser.add_argument(
        "--mode", "-m", choices=["micro", "sprint", "full"], default="full",
        help="Activation mode (default: full)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output as JSON (for programmatic use)",
    )
    parser.add_argument("--category", "-c", help="Filter by category")
    args = parser.parse_args()

    if not INDEX_PATH.exists():
        print(f"AGENTS.json not found at {INDEX_PATH}", file=sys.stderr)
        print("Run: ./scripts/generate-index.sh", file=sys.stderr)
        sys.exit(1)

    agents = load_agents()
    phase_agents = filter_by_phase(agents, args.phase)

    if args.category:
        phase_agents = [a for a in phase_agents if a["category"] == args.category]

    if not phase_agents:
        print(f"No agents found for Phase {args.phase}")
        sys.exit(1)

    if args.json:
        print(format_json(phase_agents, args.phase))
    else:
        print(format_text(phase_agents, args.phase, args.mode))


if __name__ == "__main__":
    main()
