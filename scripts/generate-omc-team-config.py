#!/usr/bin/env python3
"""Generate oh-my-claudecode team pipeline configuration from NEXUS phases.

Maps NEXUS 7-phase pipeline to OMC's 5-stage team pipeline:
  team-plan   -> NEXUS Phase 0 (Discovery) + Phase 1 (Strategy)
  team-prd    -> NEXUS Phase 1 (Strategy)
  team-exec   -> NEXUS Phase 2 (Foundation) + Phase 3 (Build)
  team-verify -> NEXUS Phase 4 (Hardening)
  team-fix    -> NEXUS Phase 3 (Build) + Phase 4 (Hardening)

Outputs a JSON config file ready to merge into .claude/omc.jsonc under "team".

Usage:
    python scripts/generate-omc-team-config.py                  # generate config
    python scripts/generate-omc-team-config.py --summary        # show mapping only
"""

import argparse
import json
from pathlib import Path
from typing import Any, cast

from _shared import REPO, atomic_write

INDEX_PATH = REPO / "AGENTS.json"
OUT_PATH = REPO / "integrations" / "oh-my-claudecode" / "team-config.json"

TEAM_STAGES = {
    "team-plan": {
        "nexus_roles": ["phase-0-discovery", "phase-1-strategy"],
        "description": "Discovery + Strategy: understand the landscape, define architecture",
        "omc_agents": ["explore", "planner", "analyst", "architect"],
    },
    "team-prd": {
        "nexus_roles": ["phase-1-strategy"],
        "description": "Write the PRD/spec from strategy outputs",
        "omc_agents": ["analyst", "critic"],
    },
    "team-exec": {
        "nexus_roles": ["phase-2-foundation", "phase-3-build"],
        "description": "Foundation + Build: scaffold and implement features",
        "omc_agents": ["executor", "debugger", "designer", "writer", "test-engineer"],
    },
    "team-verify": {
        "nexus_roles": ["phase-4-hardening"],
        "description": "Hardening: quality gate, security, compliance, performance",
        "omc_agents": ["verifier", "test-engineer", "security-reviewer", "code-reviewer"],
    },
    "team-fix": {
        "nexus_roles": ["phase-3-build", "phase-4-hardening"],
        "description": "Rework: fix issues found during verification, return to build",
        "omc_agents": ["executor", "debugger"],
    },
}


def load_agents() -> list[dict[str, Any]]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f)["agents"])


def agents_for_roles(agents: list[dict[str, Any]], roles: list[str]) -> list[dict[str, Any]]:
    return sorted(
        [a for a in agents if any(r in (a.get("nexus_roles") or []) for r in roles)],
        key=lambda a: (a["category"], a["name"]),
    )


def build_team_config(agents: list[dict]) -> dict:
    config: dict[str, dict] = {}
    for stage_name, stage_def in TEAM_STAGES.items():
        matched = agents_for_roles(agents, list(stage_def["nexus_roles"]))
        categories = sorted({a["category"] for a in matched})
        config[stage_name] = {
            "description": stage_def["description"],
            "nexus_roles": stage_def["nexus_roles"],
            "omc_lead_agents": stage_def["omc_agents"],
            "nexus_agent_count": len(matched),
            "nexus_categories": categories,
            "nexus_agents": [a["id"] for a in matched[:30]],
        }
    return config


def show_summary(config: dict) -> None:
    print("NEXUS -> OMC Team Pipeline Mapping")
    print("=" * 60)
    for stage_name, stage in config.items():
        total = stage["nexus_agent_count"]
        cats = len(stage["nexus_categories"])
        print(f"\n  {stage_name}")
        print(f"    {stage['description']}")
        print(f"    NEXUS agents: {total} across {cats} categories")
        print(f"    OMC lead: {', '.join(stage['omc_lead_agents'])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate OMC team pipeline config from NEXUS phases")
    parser.add_argument("--summary", action="store_true", help="Show mapping only")
    parser.add_argument("--output", type=Path, default=OUT_PATH,
                        help=f"Output path (default: {OUT_PATH})")
    args = parser.parse_args()

    agents = load_agents()
    config = build_team_config(agents)
    show_summary(config)

    if not args.summary:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        atomic_write(args.output,
                     json.dumps(config, ensure_ascii=False, indent=2))
        print(f"\nTeam config written to: {args.output}")
        print("Merge into .claude/omc.jsonc under 'team.nexusPipeline'")


if __name__ == "__main__":
    main()
