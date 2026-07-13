#!/usr/bin/env python3
"""NEXUS project orchestrator — manage multi-agent project pipelines.

Query mode (backward-compatible):
    python scripts/nexus-orchestrator.py --phase 0
    python scripts/nexus-orchestrator.py --phase 3 --mode sprint --json

Project mode:
    python scripts/nexus-orchestrator.py --init my-project --scenario software
    python scripts/nexus-orchestrator.py --project my-project --status
    python scripts/nexus-orchestrator.py --project my-project --start 0
    python scripts/nexus-orchestrator.py --project my-project --gate 0
    python scripts/nexus-orchestrator.py --project my-project --complete 0
    python scripts/nexus-orchestrator.py --project my-project --rollback 4
    python scripts/nexus-orchestrator.py --project my-project --report
    python scripts/nexus-orchestrator.py --list-projects

Scenarios use custom phase labels (research: Draft; consulting: Analysis; etc.)
Feedback loops enable rollback (Phase 4 issues -> Phase 3 rework; Phase 6 feedback -> Phase 0).
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "AGENTS.json"
PROJECTS_DIR = REPO / "nexus-projects"

PHASE_LABELS = {
    "0": "Discovery", "1": "Strategy", "2": "Foundation",
    "3": "Build", "4": "Hardening", "5": "Launch", "6": "Operate",
}
PHASE_TO_ROLE = {k: f"phase-{k}-{v.lower()}" for k, v in PHASE_LABELS.items()}

SCENARIOS = {
    "software": {
        "name": "Software Product Development",
        "duration": "12-24 weeks", "agents": "15-25",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
        "phase_labels": {
            "0": "Discovery", "1": "Strategy", "2": "Foundation",
            "3": "Build", "4": "Hardening", "5": "Launch", "6": "Operate",
        },
        "feedback": {"4": "3", "6": "0", "5": "3"},
        "runbook": "docs/runbooks/scenario-startup-mvp.md",
    },
    "research": {
        "name": "Research Report / White Paper",
        "duration": "2-4 weeks", "agents": "8-12",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
        "phase_labels": {
            "0": "Scope & Question", "1": "Outline & Method",
            "2": "Literature & Data", "3": "Draft & Analyze",
            "4": "Verify & Peer Review", "5": "Publish & Distribute",
            "6": "Track & Update",
        },
        "feedback": {"4": "3", "6": "0"},
        "runbook": "docs/runbooks/scenario-research-report.md",
    },
    "consulting": {
        "name": "Strategy Consulting Engagement",
        "duration": "4-8 weeks", "agents": "10-15",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
        "phase_labels": {
            "0": "Client Intake", "1": "Hypothesis & Framework",
            "2": "Data & Baseline", "3": "Analysis & Modeling",
            "4": "Stress-Test & Review", "5": "Present & Deliver",
            "6": "Implement & Support",
        },
        "feedback": {"4": "3", "6": "0"},
        "runbook": "docs/runbooks/scenario-strategy-consulting.md",
    },
    "education": {
        "name": "Course / Curriculum Design",
        "duration": "3-6 weeks", "agents": "8-12",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
        "phase_labels": {
            "0": "Needs Analysis", "1": "Objectives & Map",
            "2": "Template & Sources", "3": "Content Creation",
            "4": "Review & Align", "5": "Publish & Onboard",
            "6": "Iterate & Facilitate",
        },
        "feedback": {"4": "3", "6": "0"},
        "runbook": "docs/runbooks/scenario-course-design.md",
    },
}

GATE_QUESTIONS = {
    "0": [
        ("Market opportunity validated?", "Describe the data or evidence supporting market demand."),
        ("User pain points identified?", "List at least 3 validated user pain points with sources."),
        ("Key sources collected?", "Confirm literature, data, or documents gathered for analysis."),
        ("Compliance/regulatory clear?", "Note any regulatory review completed or not applicable."),
        ("Problem statement specific?", "State the problem in one sentence — is it answerable and scoped?"),
    ],
    "1": [
        ("Strategy covers all requirements?", "Confirm requirement coverage and note any gaps."),
        ("Architecture/outline approved?", "Who reviewed and approved the architecture/outline?"),
        ("Work plan with deadlines?", "Confirm tasks are assigned with estimated completion dates."),
        ("Quality criteria defined?", "What measurable standards define 'done' for each deliverable?"),
        ("Stakeholders aligned?", "Confirm all stakeholders have signed off on scope and approach."),
    ],
    "2": [
        ("Infrastructure operational?", "Confirm tools, environments, and platforms are ready."),
        ("Data/sources catalogued?", "Describe what data/sources are collected and organized."),
        ("Templates defined?", "What templates or standards have been established?"),
        ("Ready for build phase?", "Confirm no blocking prerequisites remain."),
        ("Prerequisites verified?", "List prerequisites and their verification status."),
    ],
    "3": [
        ("All tasks completed?", "Confirm task completion percentage and note outstanding items."),
        ("Deliverables match specs?", "How was specification compliance verified?"),
        ("Internal review done?", "Who reviewed the deliverables and what was the outcome?"),
        ("No critical issues?", "List any outstanding issues and their severity."),
        ("Artifacts organized?", "Where are build artifacts stored and how are they accessed?"),
    ],
    "4": [
        ("Quality checks passed?", "List quality metrics (test pass rate, coverage %, lint score)."),
        ("Security/compliance validated?", "Confirm security review, vulnerability scan, or compliance check results."),
        ("Performance verified?", "Provide key performance metrics (latency, throughput, etc.)."),
        ("Peer review completed?", "Who reviewed and what changes were made based on feedback?"),
        ("Documentation complete?", "Confirm documentation is accurate, current, and accessible."),
    ],
    "5": [
        ("Launch successful?", "Describe deployment outcome — downtime, errors, rollback needed?"),
        ("Stable for 48 hours?", "Confirm system stability metrics for the first 48 hours post-launch."),
        ("Feedback channels open?", "List active feedback channels and response procedures."),
        ("Stakeholders notified?", "Who was notified and when?"),
        ("Monitoring active?", "Confirm dashboards, alerts, and on-call rotation are operational."),
    ],
    "6": [
        ("SLO compliance maintained?", "Provide SLO/SLA compliance data for the review period."),
        ("Incidents < threshold?", "Count of P0/P1/P2 incidents and trend vs previous period."),
        ("Periodic review done?", "Confirm review cadence and key findings from last review."),
        ("Improvement backlog active?", "List top improvement items and their status."),
        ("Metrics positive?", "Show key metrics trend (↑/↓/→) for the review period."),
    ],
}

MODE_LIMITS = {"micro": 10, "sprint": 25, "full": 999}
COMPACT_PER_CAT = 2  # agents shown per category in compact mode (no --verbose)


# ---- Data ----

def load_agents() -> list[dict]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)["agents"]


def filter_by_phase(agents: list[dict], phase: str) -> list[dict]:
    role = PHASE_TO_ROLE[phase]
    return [a for a in agents if role in (a.get("nexus_roles") or [])]


def get_phase_label(scenario: str, phase: str) -> str:
    """Get scenario-specific phase label, falling back to default."""
    sc = SCENARIOS.get(scenario, {})
    labels = sc.get("phase_labels", PHASE_LABELS)
    return labels.get(phase, PHASE_LABELS.get(phase, f"Phase {phase}"))


def get_feedback_loops(scenario: str) -> dict[str, str]:
    """Return {phase: rollback_target} for scenario feedback loops."""
    return SCENARIOS.get(scenario, {}).get("feedback", {"4": "3", "6": "0"})


# ---- Project management ----

def checkpoint_path(name: str) -> Path:
    return PROJECTS_DIR / name / "checkpoint.json"


def create_checkpoint(name: str, scenario: str) -> dict:
    return {
        "project": name, "scenario": scenario,
        "created": datetime.now(UTC).isoformat(),
        "updated": datetime.now(UTC).isoformat(),
        "current_phase": None,
        "phases": {
            p: {"status": "pending", "started": None, "completed": None, "gate": {}}
            for p in SCENARIOS[scenario]["phases"]
        },
    }


def load_checkpoint(name: str) -> dict:
    path = checkpoint_path(name)
    if not path.exists():
        print(f"Project '{name}' not found. Use --init to create it.", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text(encoding="utf-8"))


def save_checkpoint(name: str, data: dict) -> None:
    data["updated"] = datetime.now(UTC).isoformat()
    proj_dir = PROJECTS_DIR / name
    proj_dir.mkdir(parents=True, exist_ok=True)
    (proj_dir / "checkpoint.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n"
    )


def init_project(name: str, scenario: str) -> None:
    if checkpoint_path(name).exists():
        print(f"Project '{name}' already exists. Use --status to view.", file=sys.stderr)
        sys.exit(1)
    cp = create_checkpoint(name, scenario)
    save_checkpoint(name, cp)
    sc = SCENARIOS[scenario]
    print(f"Created project '{name}' ({sc['name']})")
    print(f"  Duration: {sc['duration']}  |  Agents: {sc['agents']}")
    print(f"  Phases: {' → '.join(sc['phases'])}")
    print(f"  Runbook: {sc['runbook']}")
    print(f"  Checkpoint: {checkpoint_path(name)}")
    print(f"\nNext: python scripts/nexus-orchestrator.py --project {name} --start 0")


def show_status(name: str) -> None:
    cp = load_checkpoint(name)
    sc = SCENARIOS[cp["scenario"]]
    print(f"Project: {name} ({sc['name']})")
    print(f"Created: {cp['created'][:10]}  |  Scenario: {cp['scenario']}")
    print("\nPhase Status:")
    for p in sc["phases"]:
        ps = cp["phases"][p]
        icon = {"pending": "○", "in_progress": "▶", "completed": "✔"}.get(ps["status"], "?")
        extra = ""
        if ps["started"]:
            extra += f"  {ps['started'][:10]}"
        if ps["completed"]:
            extra += f" → {ps['completed'][:10]}"
        label = get_phase_label(cp["scenario"], p)
        print(f"  {icon} Phase {p} - {label:<22} {ps['status']:<12}{extra}")
    current = cp.get("current_phase")
    if current and cp["phases"][current]["status"] == "in_progress":
        label = get_phase_label(cp["scenario"], current)
        print(f"\nActive: Phase {current} ({label})")
        print(f"  --start {current} to see agent roster")
        print(f"  --gate {current} to run quality checklist")
        print(f"  --rollback {current} to return for rework")
    fb = get_feedback_loops(cp["scenario"])
    if fb:
        print("\nFeedback Loops:")
        for from_p, to_p in sorted(fb.items()):
            fl = get_phase_label(cp["scenario"], from_p)
            tl = get_phase_label(cp["scenario"], to_p)
            print(f"  {fl} (P{from_p}) --found issues--> {tl} (P{to_p})")


def start_phase(name: str, phase: str, verbose: bool = False) -> None:
    cp = load_checkpoint(name)
    prev = str(int(phase) - 1)
    if prev in cp["phases"] and cp["phases"][prev]["status"] != "completed":
        print(f"ERROR: Phase {prev} must be completed first.", file=sys.stderr)
        sys.exit(1)
    ps = cp["phases"][phase]
    ps["status"] = "in_progress"
    ps["started"] = datetime.now(UTC).isoformat()
    cp["current_phase"] = phase
    save_checkpoint(name, cp)
    # Output agent roster
    agents = load_agents()
    phase_agents = filter_by_phase(agents, phase)
    by_cat: dict[str, list[dict]] = {}
    for a in phase_agents:
        by_cat.setdefault(a["category"], []).append(a)
    phase_label = get_phase_label(cp["scenario"], phase)
    print(f"\nPhase {phase} — {phase_label}  [▶ IN PROGRESS]")
    print("=" * 55)
    playbook_path = f"docs/playbooks/phase-{phase}-{PHASE_LABELS[phase].lower()}.md"
    print(f"\nPlaybook: {playbook_path}")
    print(f"Available: {len(phase_agents)} agents across {len(by_cat)} categories")

    limit = COMPACT_PER_CAT if not verbose else 999
    shown = 0
    for cat in sorted(by_cat):
        agents_in_cat = sorted(by_cat[cat], key=lambda a: a["name"])
        display = agents_in_cat[:limit]
        remaining = len(agents_in_cat) - len(display)
        if verbose or len(phase_agents) <= 20 or remaining == 0:
            print(f"\n  [{cat}]  ({len(agents_in_cat)} agents)")
        else:
            print(f"\n  [{cat}]  ({len(agents_in_cat)} agents — showing top {limit})")
        for a in display:
            print(f"    - {a['name']}  ({a['id']})")
            shown += 1
        if remaining > 0:
            print(f"    ... +{remaining} more")
    if not verbose and len(phase_agents) > 20:
        remaining = len(phase_agents) - shown
        print(f"\n  ({remaining} agents hidden — use --verbose for full listing)")

    print(f"\nQuality Gate ({phase_label}):")
    for q, desc in GATE_QUESTIONS[phase]:
        print(f"  ☐ {q}")
        print(f"    ({desc})")
    print(f"\nReference: {playbook_path}")


def run_gate(name: str, phase: str) -> None:
    cp = load_checkpoint(name)
    ps = cp["phases"][phase]
    if ps["status"] != "in_progress":
        print(f"Phase {phase} is {ps['status']}. Use --start {phase} first.", file=sys.stderr)
        sys.exit(1)
    print(f"\nPhase {phase} — {PHASE_LABELS[phase]}  [GATE CHECK]")
    print("=" * 55)
    print("For each question, enter: pass|fail [evidence or explanation]")
    print()

    gate = {}
    for question, desc in GATE_QUESTIONS[phase]:
        print(f"  [{question}]")
        print(f"  ({desc})")
        ans = input("  > ").strip()
        parts = ans.split(maxsplit=1)
        passed = parts and parts[0].lower() in ("pass", "p", "yes", "y")
        evidence = parts[1] if len(parts) > 1 else ""
        gate[question] = {"passed": passed, "evidence": evidence, "timestamp": datetime.now(UTC).isoformat()}
        icon = "✓ PASS" if passed else "✗ FAIL"
        if evidence:
            print(f"    {icon} — {evidence}")
        else:
            print(f"    {icon}")
        print()

    ps["gate"] = gate
    save_checkpoint(name, cp)
    if all(g["passed"] for g in gate.values()):
        print(f"All checks passed. Run --complete {phase} to advance.")
    else:
        failed = [q for q, g in gate.items() if not g["passed"]]
        print(f"{len(failed)} check(s) failed: {', '.join(failed[:3])}")
        print(f"Resolve issues and re-run --gate {phase}.")


def generate_report(name: str) -> None:
    cp = load_checkpoint(name)
    sc = SCENARIOS[cp["scenario"]]
    print(f"\n{'=' * 60}")
    print("NEXUS GATE REPORT")
    print(f"Project: {name} ({sc['name']})")
    print(f"Scenario: {cp['scenario']}  |  Created: {cp['created'][:10]}")
    print(f"{'=' * 60}")

    total_gates = 0
    passed_gates = 0
    for p in sc["phases"]:
        ps = cp["phases"][p]
        if ps["status"] not in ("completed", "in_progress"):
            continue
        print(f"\nPhase {p} — {PHASE_LABELS[p]} [{ps['status'].upper()}]")
        if ps["started"]:
            print(f"  Started: {ps['started'][:10]}")
        if ps["completed"]:
            print(f"  Completed: {ps['completed'][:10]}")

        gate = ps.get("gate", {})
        if gate:
            for question, result in gate.items():
                if isinstance(result, dict):
                    icon = "✓" if result["passed"] else "✗"
                    evidence = f" — {result['evidence']}" if result.get("evidence") else ""
                    print(f"  {icon} {question}{evidence}")
                    total_gates += 1
                    if result["passed"]:
                        passed_gates += 1
                else:
                    # Legacy format support
                    icon = "✓" if result else "✗"
                    print(f"  {icon} {question}")
                    total_gates += 1
                    if result:
                        passed_gates += 1
        else:
            print("  (gate not yet run)")

    if total_gates > 0:
        print(f"\n{'─' * 60}")
        print(f"Gate Summary: {passed_gates}/{total_gates} passed ({100 * passed_gates // total_gates}%)")

    # Project progress
    completed = sum(1 for p in cp["phases"].values() if p["status"] == "completed")
    total = len(cp["phases"])
    print(f"Phase Progress: {completed}/{total} phases complete")
    print(f"{'=' * 60}")


def complete_phase(name: str, phase: str) -> None:
    cp = load_checkpoint(name)
    ps = cp["phases"][phase]
    if ps["status"] != "in_progress":
        print(f"Phase {phase} is {ps['status']}.", file=sys.stderr)
        sys.exit(1)
    gate = ps.get("gate", {})
    all_passed = all(
        (g["passed"] if isinstance(g, dict) else g) for g in gate.values()
    )
    if not gate or not all_passed:
        print("Gate not passed. Run --gate first.", file=sys.stderr)
        sys.exit(1)
    ps["status"] = "completed"
    ps["completed"] = datetime.now(UTC).isoformat()
    cp["current_phase"] = None
    save_checkpoint(name, cp)
    print(f"Phase {phase} — {PHASE_LABELS[phase]}  [✔ COMPLETED]")
    next_p = str(int(phase) + 1)
    if next_p in cp["phases"]:
        print(f"\nNext: --project {name} --start {next_p}")
    else:
        print(f"\nAll 7 phases complete! Project '{name}' is finished.")


def rollback_phase(name: str, phase: str) -> None:
    cp = load_checkpoint(name)
    ps = cp["phases"][phase]
    if ps["status"] not in ("completed", "in_progress"):
        print(f"Phase {phase} is {ps['status']}. Nothing to rollback.", file=sys.stderr)
        sys.exit(1)
    fb = get_feedback_loops(cp["scenario"])
    target = fb.get(phase)
    if not target:
        print(f"No feedback loop defined for Phase {phase}.", file=sys.stderr)
        sys.exit(1)
    # Mark current phase as in_progress (rework) and reset the target
    ps["status"] = "in_progress"
    cp["phases"][phase]["completed"] = None
    cp["phases"][phase]["gate"] = {}
    # Reopen target phase
    cp["phases"][target]["status"] = "in_progress"
    cp["phases"][target]["completed"] = None
    cp["phases"][target]["gate"] = {}
    cp["current_phase"] = target
    save_checkpoint(name, cp)
    from_label = get_phase_label(cp["scenario"], phase)
    to_label = get_phase_label(cp["scenario"], target)
    print(f"Rolled back: {from_label} (P{phase}) → {to_label} (P{target})")
    print("Both phases reopened for rework.")
    print(f"\nNext: --project {name} --start {target}")


def list_projects() -> None:
    if not PROJECTS_DIR.exists() or not any(
        d.is_dir() and (d / "checkpoint.json").exists()
        for d in PROJECTS_DIR.iterdir()
    ):
        print("No projects found. Create one with --init <name>")
        return
    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir():
            continue
        cp_file = d / "checkpoint.json"
        if not cp_file.exists():
            continue
        cp = json.loads(cp_file.read_text(encoding="utf-8"))
        sc = SCENARIOS.get(cp["scenario"], {}).get("name", cp["scenario"])
        done = sum(1 for p in cp["phases"].values() if p["status"] == "completed")
        total = len(cp["phases"])
        cur = cp.get("current_phase", "—")
        print(f"  {d.name:<20} {sc:<40} {done}/{total} done  (active: {cur})")


# ---- Legacy query mode (backward-compatible) ----

def query_phase(phase: str, mode: str, category: str | None, json_out: bool, verbose: bool = False) -> None:
    if not INDEX_PATH.exists():
        print("AGENTS.json not found. Run: python scripts/generate-index.py", file=sys.stderr)
        sys.exit(1)
    agents = load_agents()
    phase_agents = filter_by_phase(agents, phase)
    if category:
        phase_agents = [a for a in phase_agents if a["category"] == category]
    if not phase_agents:
        print(f"No agents found for Phase {phase}")
        sys.exit(1)
    if json_out:
        print(json.dumps({
            "phase": phase, "label": PHASE_LABELS[phase],
            "agent_count": len(phase_agents),
            "agents": [{"id": a["id"], "name": a["name"], "category": a["category"]} for a in phase_agents],
        }, ensure_ascii=False, indent=2))
        return
    by_cat: dict[str, list[dict]] = {}
    for a in phase_agents:
        by_cat.setdefault(a["category"], []).append(a)
    print(f"NEXUS Phase {phase} — {PHASE_LABELS[phase]} ({mode.title()} Mode)")
    print("=" * 55)
    print(f"Playbook: docs/playbooks/phase-{phase}-{PHASE_LABELS[phase].lower()}.md")
    print(f"Available: {len(phase_agents)} agents across {len(by_cat)} categories\n")

    limit = MODE_LIMITS[mode]
    if not verbose and len(phase_agents) > 20:
        limit = min(limit, COMPACT_PER_CAT * len(by_cat))
    n = 0
    for cat in sorted(by_cat):
        agents_in_cat = sorted(by_cat[cat], key=lambda a: a["name"])
        if verbose or len(phase_agents) <= 20 or (len(agents_in_cat) - COMPACT_PER_CAT <= 0):
            print(f"  [{cat}]  ({len(agents_in_cat)} agents)")
        else:
            print(f"  [{cat}]  ({len(agents_in_cat)} agents — showing top {COMPACT_PER_CAT})")
        for a in agents_in_cat:
            if n >= limit:
                break
            print(f"    - {a['name']}")
            n += 1
        if n >= limit:
            remaining = len(phase_agents) - n
            print(f"\n  ... +{remaining} more (use --mode full or --verbose)")
            break
    print(f"\nTotal: {len(phase_agents)} agents for Phase {phase}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="NEXUS multi-agent project orchestrator")
    # Project commands
    parser.add_argument("--init", help="Create a new NEXUS project")
    parser.add_argument("--scenario", choices=list(SCENARIOS), default="software")
    parser.add_argument("--project", "-P", help="Project name")
    parser.add_argument("--status", action="store_true", help="Show project status")
    parser.add_argument("--start", choices=["0","1","2","3","4","5","6"], help="Start a phase")
    parser.add_argument("--gate", choices=["0","1","2","3","4","5","6"], help="Run gate checklist")
    parser.add_argument("--complete", choices=["0","1","2","3","4","5","6"], help="Complete a phase")
    parser.add_argument("--rollback", choices=["0","1","2","3","4","5","6"], help="Rollback a phase via feedback loop")
    parser.add_argument("--list-projects", action="store_true", help="List all projects")
    parser.add_argument("--report", action="store_true", help="Generate gate report for a project")
    # Legacy query mode
    parser.add_argument("--phase", "-p", choices=["0","1","2","3","4","5","6"], help="Query agents for a phase")
    parser.add_argument("--mode", "-m", choices=["micro","sprint","full"], default="full")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full agent listing")
    args = parser.parse_args()

    if args.list_projects:
        list_projects()
        return
    if args.init:
        init_project(args.init, args.scenario)
        return
    if args.project:
        if args.report:
            generate_report(args.project)
        elif args.status:
            show_status(args.project)
        elif args.start:
            start_phase(args.project, args.start, verbose=args.verbose)
        elif args.gate:
            run_gate(args.project, args.gate)
        elif args.complete:
            complete_phase(args.project, args.complete)
        elif args.rollback:
            rollback_phase(args.project, args.rollback)
        else:
            show_status(args.project)
        return
    if args.phase:
        query_phase(args.phase, args.mode, args.category, args.json, verbose=args.verbose)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
