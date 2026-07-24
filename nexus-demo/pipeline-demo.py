#!/usr/bin/env python
"""NEXUS Pipeline Demo — end-to-end orchestration proof-of-concept.

Demonstrates the 7-phase NEXUS pipeline by reading agent nexus_roles and
simulating a sample project workflow. Does NOT invoke LLMs — this is a
structural validation of the orchestration framework.

Usage:
    python nexus-demo/pipeline-demo.py              # full pipeline report
    python nexus-demo/pipeline-demo.py --phase 3     # single phase detail
    python nexus-demo/pipeline-demo.py --scenario web-app  # scenario-based
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

from _shared import discover_agents, get_frontmatter_text, get_list_field

PHASES = [
    ("phase-0-discovery", "Phase 0: Discovery", "Intelligence gathering & analysis"),
    ("phase-1-strategy", "Phase 1: Strategy", "Architecture & planning"),
    ("phase-2-foundation", "Phase 2: Foundation", "Scaffolding & setup"),
    ("phase-3-build", "Phase 3: Build", "Core development"),
    ("phase-4-hardening", "Phase 4: Hardening", "Quality & security"),
    ("phase-5-launch", "Phase 5: Launch", "Deployment & go-to-market"),
    ("phase-6-operate", "Phase 6: Operate", "Monitoring & maintenance"),
]

SCENARIOS = {
    "web-app": {
        "name": "Web Application",
        "categories": ["engineering", "design", "data-science", "testing",
                       "operations", "cybersecurity", "marketing"],
    },
    "data-pipeline": {
        "name": "Data Pipeline",
        "categories": ["data-science", "engineering", "infrastructure",
                       "operations", "iot"],
    },
    "mobile-app": {
        "name": "Mobile Application",
        "categories": ["engineering", "design", "testing", "marketing",
                       "operations", "cybersecurity"],
    },
}


def load_agent_nexus_data():
    """Discover all agents and extract their NEXUS phase assignments."""
    agents = []
    for _cat, _rel, filepath in discover_agents():
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            continue
        fm = get_frontmatter_text(content)
        nexus_roles = get_list_field("nexus_roles", fm)
        if nexus_roles:
            agents.append({
                "id": filepath.stem,
                "category": filepath.parent.name,
                "nexus_roles": nexus_roles,
            })
    return agents


def build_phase_distribution(agents):
    """Organize agents by NEXUS phase."""
    phases = defaultdict(list)
    for agent in agents:
        for role in agent["nexus_roles"]:
            phases[role].append(agent)
    return dict(phases)


def print_pipeline_overview(phases):
    """Print the full 7-phase pipeline overview."""
    print("\n" + "=" * 70)
    print("  NEXUS Pipeline — Phase Distribution")
    print("=" * 70)

    for phase_key, phase_name, _desc in PHASES:
        agents = phases.get(phase_key, [])
        bar = "█" * min(len(agents) // 10, 40)
        print(f"\n  {phase_name}")
        print(f"  {'─' * 50}")
        print(f"  Agents: {len(agents):>4}  {bar}")

    print(f"\n  {'─' * 50}")


def print_phase_detail(phases, phase_key):
    """Print detailed agent list for a specific phase."""
    agents = phases.get(phase_key, [])
    print(f"\n  {'─' * 60}")
    print(f"  {len(agents)} agents assigned")
    by_cat = defaultdict(list)
    for a in agents:
        by_cat[a["category"]].append(a["id"])
    for cat in sorted(by_cat):
        print(f"  {cat}: {', '.join(by_cat[cat][:5])}")
        if len(by_cat[cat]) > 5:
            print(f"       ... and {len(by_cat[cat]) - 5} more")


def simulate_scenario(phases, scenario_key):
    """Simulate a NEXUS pipeline run for a specific scenario."""
    scenario = SCENARIOS.get(scenario_key)
    if not scenario:
        print(f"Unknown scenario: {scenario_key}")
        return

    print("\n" + "=" * 70)
    print(f"  NEXUS Simulation: {scenario['name']}")
    print("=" * 70)

    for phase_key, phase_name, desc in PHASES:
        all_agents = phases.get(phase_key, [])
        relevant = [a for a in all_agents
                    if a["category"] in scenario["categories"]]
        total = len(all_agents)

        print(f"\n  [{phase_name}] {desc}")
        print(f"  Available: {len(relevant)} relevant (of {total} total)")

        if relevant:
            top = sorted(relevant, key=lambda a: len(a["nexus_roles"]),
                        reverse=True)[:3]
            for a in top:
                roles = ", ".join(a["nexus_roles"])
                print(f"    -> {a['id']} ({a['category']}) [{roles}]")

    print("\n  " + "-" * 60)
    print("  Pipeline Health:")
    for phase_key, phase_name, _desc in PHASES:
        all_agents = phases.get(phase_key, [])
        relevant = [a for a in all_agents
                    if a["category"] in scenario["categories"]]
        if not relevant:
            print(f"  {'WARNING':10s} {phase_name}: no relevant agents")
        elif len(relevant) < 3:
            print(f"  {'WARNING':10s} {phase_name}: only {len(relevant)} agents")
        else:
            print(f"  {'OK':10s} {phase_name}: {len(relevant)} agents")


def main():
    parser = argparse.ArgumentParser(description="NEXUS Pipeline Demo")
    parser.add_argument("--phase", type=int, choices=range(0, 7),
                        help="Show detail for a specific phase (0-6)")
    parser.add_argument("--scenario", choices=list(SCENARIOS),
                        help="Simulate pipeline for a specific scenario")
    args = parser.parse_args()

    agents = load_agent_nexus_data()
    phases = build_phase_distribution(agents)

    if not phases:
        print("No agents with nexus_roles found. Run scripts/batch-nexus-roles.py first.")
        return

    if args.phase is not None:
        for pk, _, _ in PHASES:
            if pk.startswith(f"phase-{args.phase}-"):
                print_phase_detail(phases, pk)
                break
    elif args.scenario:
        simulate_scenario(phases, args.scenario)
    else:
        print_pipeline_overview(phases)
        print("\n  Use --phase 0-6 for details or --scenario for simulation")


if __name__ == "__main__":
    main()
