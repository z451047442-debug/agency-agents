#!/usr/bin/env python3
"""Generate oh-my-claudecode SKILL.md files for each NEXUS pipeline phase.

Each skill maps to one NEXUS phase, listing the agents registered for that
phase, the quality gate checklist, and activation instructions. A combined
"nexus-full" skill covers the entire 7-phase pipeline.

Usage:
    python scripts/generate-nexus-skills.py                    # all phases
    python scripts/generate-nexus-skills.py --phase 0          # single phase
    python scripts/generate-nexus-skills.py --check            # verify output is up to date
"""

import argparse
import json
import sys
from datetime import datetime

from _shared import REPO, atomic_write

INDEX_PATH = REPO / "AGENTS.json"
OUT_DIR = REPO / "integrations" / "oh-my-claudecode" / "skills"

PHASES = {
    "0": {
        "label": "Discovery",
        "keyword": "discover",
        "triggers": ["discover", "research", "market analysis", "user research",
                     "discovery", "调研", "发现", "探索"],
        "objective": "Understand the landscape before committing resources. "
                     "Validate the problem, market, and user needs.",
        "gate_keeper": "Executive Summary Generator",
    },
    "1": {
        "label": "Strategy",
        "keyword": "strategize",
        "triggers": ["strategize", "architecture", "strategy", "planning", "roadmap",
                     "架构", "战略", "规划", "路线图"],
        "objective": "Define what to build, how it's structured, and what success "
                     "looks like — before writing any code.",
        "gate_keeper": "Studio Producer + Reality Checker (dual sign-off)",
    },
    "2": {
        "label": "Foundation",
        "keyword": "scaffold",
        "triggers": ["scaffold", "foundation", "setup", "infrastructure", "CI/CD",
                     "脚手架", "基础", "基础设施"],
        "objective": "Build the technical and operational foundation. Get the "
                     "skeleton standing before adding muscle.",
        "gate_keeper": "DevOps Automator + Evidence Collector",
    },
    "3": {
        "label": "Build",
        "keyword": "build",
        "triggers": ["build", "implement", "develop", "feature",
                     "构建", "开发", "实现"],
        "objective": "Implement features through continuous Dev↔QA loops. Every "
                     "task validated before the next begins.",
        "gate_keeper": "Agents Orchestrator",
    },
    "4": {
        "label": "Hardening",
        "keyword": "harden",
        "triggers": ["harden", "quality gate", "QA", "testing", "security audit",
                     "加固", "质量门", "测试", "安全审计"],
        "objective": "Final quality gauntlet. Default verdict is NEEDS WORK — "
                     "must prove production readiness with overwhelming evidence.",
        "gate_keeper": "Reality Checker (sole authority)",
    },
    "5": {
        "label": "Launch",
        "keyword": "launch",
        "triggers": ["launch", "deploy", "release", "go live", "ship",
                     "发布", "上线", "部署"],
        "objective": "Coordinate go-to-market execution across all channels. "
                     "Maximum impact at launch.",
        "gate_keeper": "Studio Producer + Analytics Reporter",
    },
    "6": {
        "label": "Operate",
        "keyword": "operate",
        "triggers": ["operate", "monitor", "maintain", "support", "sustain",
                     "运维", "运营", "监控", "维护"],
        "objective": "Sustained operations with continuous improvement. The "
                     "product is live — make it thrive.",
        "gate_keeper": "Infrastructure Maintainer + Analytics Reporter",
    },
}

GATE_QUESTIONS = {
    "0": [
        "Market opportunity validated? (TAM > minimum viable)",
        "User need confirmed? (>=3 validated pain points)",
        "Regulatory path clear? (no blocking compliance issues)",
        "Data foundation assessed? (key metrics identified)",
        "Technology feasibility confirmed? (stack validated)",
    ],
    "1": [
        "Strategy covers all requirements? (100% spec coverage)",
        "Architecture approved? (all components have implementation path)",
        "Brand system complete? (logo, colors, typography, voice defined)",
        "Budget approved? (within organizational constraints)",
        "Sprint plan realistic? (velocity-based estimation)",
        "Security architecture defined? (threat model + controls documented)",
    ],
    "2": [
        "CI/CD pipeline operational? (build + test + deploy working)",
        "Database schema deployed? (all tables/indexes created)",
        "API scaffold responding? (health check endpoints live)",
        "Frontend rendering? (skeleton app loads in browser)",
        "Monitoring active? (dashboards showing metrics)",
        "Design system implemented? (tokens + components available)",
    ],
    "3": [
        "All tasks pass QA? (100% task completion with PASS)",
        "API endpoints validated? (all endpoints tested)",
        "Performance baselines met? (P95 < 200ms, LCP < 2.5s)",
        "Brand consistency verified? (95%+ adherence)",
        "No critical bugs? (zero P0/P1 open)",
        "Code review completed? (all PRs reviewed and approved)",
    ],
    "4": [
        "User journeys complete? (all critical paths working)",
        "Cross-device consistency? (desktop + tablet + mobile verified)",
        "Security validated? (zero critical vulnerabilities)",
        "Compliance certified? (all regulatory requirements met)",
        "Infrastructure ready? (production environment validated)",
        "Specification compliance? (100% spec verified point-by-point)",
    ],
    "5": [
        "Deployment successful? (zero-downtime, all health checks pass)",
        "Systems stable for 48h? (no P0/P1 incidents)",
        "User acquisition active? (channels driving traffic)",
        "Feedback loop operational? (user feedback being collected)",
        "Support operational? (response time < 1h)",
    ],
    "6": [
        "SLO compliance maintained? (SLO targets met)",
        "Incidents under threshold? (trend stable or decreasing)",
        "Periodic review done? (review cadence met)",
        "Improvement backlog active? (items tracked with owner)",
        "Metrics positive? (key metrics trending up)",
    ],
}


def load_agents() -> list[dict]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)["agents"]


def agents_for_phase(agents: list[dict], phase: str) -> list[dict]:
    role = f"phase-{phase}-{PHASES[phase]['label'].lower()}"
    return sorted(
        [a for a in agents if role in (a.get("nexus_roles") or [])],
        key=lambda a: (a["category"], a["name"]),
    )


def build_skill_md(phase: str, agents: list[dict]) -> str:
    p = PHASES[phase]
    phase_agents = agents_for_phase(agents, phase)

    by_cat: dict[str, list[str]] = {}
    for a in phase_agents:
        by_cat.setdefault(a["category"], []).append(f"- {a['name']} (`{a['id']}`)")

    agent_list = ""
    for cat in sorted(by_cat):
        agent_list += f"\n**{cat}** ({len(by_cat[cat])} agents)\n"
        for line in by_cat[cat]:
            agent_list += f"{line}\n"

    gate = ""
    for i, q in enumerate(GATE_QUESTIONS.get(phase, []), 1):
        gate += f"{i}. ☐ {q}\n"

    triggers = ", ".join(f"`{t}`" for t in p["triggers"][:5])

    return f"""---
name: nexus-{p['keyword']}
description: NEXUS Phase {phase} — {p['label']} pipeline stage for multi-agent orchestration
argument-hint: "[project-name] <task description>"
triggers: [{', '.join(p['triggers'])}]
category: nexus
source: agency-agents
version: "1.0"
generated: {datetime.now().isoformat()[:10]}
---

# NEXUS Phase {phase}: {p['label']}

## Objective

{p['objective']}

## Agent Roster

This phase activates **{len(phase_agents)} agents** across {len(by_cat)} categories.
{agent_list}
## Quality Gate

**Gate Keeper**: {p['gate_keeper']}

All items must pass before advancing to Phase {int(phase) + 1}:
{gate}
## Activation

Say any of these to activate this phase: {triggers}

When activated, follow the NEXUS playbook at `docs/playbooks/phase-{phase}-{p['label'].lower()}.md`.

## Handoff Protocol

Every agent-to-agent handoff must include:
- **Context**: project name, current state, relevant files
- **Deliverable**: specific, measurable output with acceptance criteria
- **Evidence**: proof of completion (screenshots, logs, test results)
- **Receiver**: which agent receives the output and what they need

## Escalation

If a task fails QA 3 times, escalate to the Gate Keeper with:
- Failure history (all 3 attempts)
- Root cause analysis
- Recommended resolution (reassign / decompose / redesign / accept / defer)
"""


def generate_phase(phase: str, agents: list[dict], check: bool) -> bool:
    p = PHASES[phase]
    skill_dir = OUT_DIR / f"nexus-{p['keyword']}"
    skill_path = skill_dir / "SKILL.md"
    content = build_skill_md(phase, agents)

    if check:
        if not skill_path.exists():
            print(f"  MISSING: {skill_path}")
            return False
        existing = skill_path.read_text(encoding="utf-8")
        if existing != content:
            print(f"  STALE: {skill_path}")
            return False
        return True

    skill_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(skill_path, content)
    print(f"  wrote: {skill_path} ({len(agents_for_phase(agents, phase))} agents)")
    return True


def generate_full(agents: list[dict], check: bool) -> bool:
    """Generate a combined NEXUS-Full skill covering all phases."""
    skill_dir = OUT_DIR / "nexus-full"
    skill_path = skill_dir / "SKILL.md"

    phase_summary = ""
    for p in sorted(PHASES):
        count = len(agents_for_phase(agents, p))
        phase_summary += f"| Phase {p} | {PHASES[p]['label']} | {count} agents |\n"

    content = f"""---
name: nexus-full
description: NEXUS Full Pipeline — complete 7-phase multi-agent orchestration from Discovery to Operate
argument-hint: "<project description or spec file path>"
triggers: [nexus, full pipeline, nexus full, end to end, NEXUS, 全流程, 端到端]
category: nexus
source: agency-agents
version: "1.0"
generated: {datetime.now().isoformat()[:10]}
---

# NEXUS Full Pipeline

## Overview

The complete 7-phase NEXUS pipeline orchestrates 1,399 specialized AI agents
across 62 categories from project Discovery through sustained Operations.

## Phase Summary

| Phase | Name | Agents |
|-------|------|--------|
{phase_summary}
## Activation

Say "nexus" or "full pipeline" to start. The orchestrator will:
1. Read the project specification
2. Activate Phase 0 agents for discovery
3. Progress through all phases with quality gates
4. Manage Dev↔QA loops automatically
5. Report status at each phase boundary

## Individual Phase Skills

- `nexus-discover` — Phase 0: Intelligence & Discovery
- `nexus-strategize` — Phase 1: Strategy & Architecture
- `nexus-scaffold` — Phase 2: Foundation & Scaffolding
- `nexus-build` — Phase 3: Build & Iterate
- `nexus-harden` — Phase 4: Quality & Hardening
- `nexus-launch` — Phase 5: Launch & Growth
- `nexus-operate` — Phase 6: Operate & Evolve

## Reference

Full NEXUS strategy: `docs/nexus-strategy.md`
NEXUS cycle (feedback loops): `docs/nexus-cycle.md`
Orchestrator CLI: `python scripts/nexus-orchestrator.py --help`
"""

    if check:
        if not skill_path.exists():
            print(f"  MISSING: {skill_path}")
            return False
        existing = skill_path.read_text(encoding="utf-8")
        if existing != content:
            print(f"  STALE: {skill_path}")
            return False
        return True

    skill_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(skill_path, content)
    print(f"  wrote: {skill_path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate NEXUS skills for oh-my-claudecode")
    parser.add_argument("--phase", choices=list(PHASES), help="Generate a single phase")
    parser.add_argument("--check", action="store_true", help="Verify output is up to date")
    args = parser.parse_args()

    agents = load_agents()
    phases = [args.phase] if args.phase else sorted(PHASES)
    all_ok = True

    for p in phases:
        ok = generate_phase(p, agents, args.check)
        all_ok = all_ok and ok

    if not args.phase:
        ok = generate_full(agents, args.check)
        all_ok = all_ok and ok

    if args.check:
        if all_ok:
            print("OK: all NEXUS skills up to date")
        else:
            print("FAIL: some skills missing or stale. Re-run without --check to regenerate.")
            sys.exit(1)


if __name__ == "__main__":
    main()
