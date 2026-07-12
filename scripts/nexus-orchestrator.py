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
    python scripts/nexus-orchestrator.py --project my-project --report
    python scripts/nexus-orchestrator.py --list-projects
"""

import argparse
import json
import sys
from datetime import datetime, timezone
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
        "runbook": "docs/runbooks/scenario-startup-mvp.md",
    },
    "research": {
        "name": "Research Report / White Paper",
        "duration": "2-4 weeks", "agents": "8-12",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
        "runbook": "docs/runbooks/scenario-research-report.md",
    },
    "consulting": {
        "name": "Strategy Consulting Engagement",
        "duration": "4-8 weeks", "agents": "10-15",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
        "runbook": "docs/runbooks/scenario-strategy-consulting.md",
    },
    "education": {
        "name": "Course / Curriculum Design",
        "duration": "3-6 weeks", "agents": "8-12",
        "phases": ["0", "1", "2", "3", "4", "5", "6"],
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


# ---- Data ----

def load_agents() -> list[dict]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)["agents"]


def filter_by_phase(agents: list[dict], phase: str) -> list[dict]:
    role = PHASE_TO_ROLE[phase]
    return [a for a in agents if role in (a.get("nexus_roles") or [])]


# ---- Project management ----

def checkpoint_path(name: str) -> Path:
    return PROJECTS_DIR / name / "checkpoint.json"


def create_checkpoint(name: str, scenario: str) -> dict:
    return {
        "project": name, "scenario": scenario,
        "created": datetime.now(timezone.utc).isoformat(),
        "updated": datetime.now(timezone.utc).isoformat(),
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
    data["updated"] = datetime.now(timezone.utc).isoformat()
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
    print(f"\nPhase Status:")
    for p in sc["phases"]:
        ps = cp["phases"][p]
        icon = {"pending": "○", "in_progress": "▶", "completed": "✔"}.get(ps["status"], "?")
        extra = ""
        if ps["started"]:
            extra += f"  {ps['started'][:10]}"
        if ps["completed"]:
            extra += f" → {ps['completed'][:10]}"
        print(f"  {icon} Phase {p} - {PHASE_LABELS[p]:<12} {ps['status']:<12}{extra}")
    current = cp.get("current_phase")
    if current and cp["phases"][current]["status"] == "in_progress":
        print(f"\nActive: Phase {current} ({PHASE_LABELS[current]})")
        print(f"  --start {current} to see agent roster")
        print(f"  --gate {current} to run quality checklist")


def start_phase(name: str, phase: str) -> None:
    cp = load_checkpoint(name)
    # Check prerequisite
    prev = str(int(phase) - 1)
    if prev in cp["phases"] and cp["phases"][prev]["status"] != "completed":
        print(f"ERROR: Phase {prev} must be completed first.", file=sys.stderr)
        sys.exit(1)
    ps = cp["phases"][phase]
    ps["status"] = "in_progress"
    ps["started"] = datetime.now(timezone.utc).isoformat()
    cp["current_phase"] = phase
    save_checkpoint(name, cp)
    # Output agent roster
    agents = load_agents()
    phase_agents = filter_by_phase(agents, phase)
    by_cat: dict[str, list[dict]] = {}
    for a in phase_agents:
        by_cat.setdefault(a["category"], []).append(a)
    print(f"\nPhase {phase} — {PHASE_LABELS[phase]}  [▶ IN PROGRESS]")
    print("=" * 55)
    print(f"\nAgents to activate ({len(phase_agents)} total):\n")
    for cat in sorted(by_cat):
        shown = by_cat[cat][:12]
        print(f"  [{cat}]  ({len(by_cat[cat])} agents)")
        for a in shown:
            print(f"    - {a['name']}  ({a['id']})")
        if len(by_cat[cat]) > 12:
            print(f"    ... +{len(by_cat[cat]) - 12} more")
    print(f"\nQuality Gate ({PHASE_LABELS[phase]}):")
    for q, desc in GATE_QUESTIONS[phase]:
        print(f"  ☐ {q}")
        print(f"    ({desc})")
    print(f"\nReference: docs/playbooks/phase-{phase}-{PHASE_LABELS[phase].lower()}.md")


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
        ans = input(f"  > ").strip()
        parts = ans.split(maxsplit=1)
        passed = parts and parts[0].lower() in ("pass", "p", "yes", "y")
        evidence = parts[1] if len(parts) > 1 else ""
        gate[question] = {"passed": passed, "evidence": evidence, "timestamp": datetime.now(timezone.utc).isoformat()}
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
    print(f"NEXUS GATE REPORT")
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
            print(f"  (gate not yet run)")

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
    ps["completed"] = datetime.now(timezone.utc).isoformat()
    cp["current_phase"] = None
    save_checkpoint(name, cp)
    print(f"Phase {phase} — {PHASE_LABELS[phase]}  [✔ COMPLETED]")
    next_p = str(int(phase) + 1)
    if next_p in cp["phases"]:
        print(f"\nNext: --project {name} --start {next_p}")
    else:
        print(f"\nAll 7 phases complete! Project '{name}' is finished.")


def list_projects() -> None:
    if not PROJECTS_DIR.exists() or not any(
        d.is_dir() and (d / "checkpoint.json").exists()
        for d in PROJECTS_DIR.iterdir()
    ):
        print("No projects found. Create one with --init <name>")
        return
    for d in sorted(PROJECTS_DIR.iterdir()):
        if not d.is_dir(): continue
        cp_file = d / "checkpoint.json"
        if not cp_file.exists(): continue
        cp = json.loads(cp_file.read_text(encoding="utf-8"))
        sc = SCENARIOS.get(cp["scenario"], {}).get("name", cp["scenario"])
        done = sum(1 for p in cp["phases"].values() if p["status"] == "completed")
        total = len(cp["phases"])
        cur = cp.get("current_phase", "—")
        print(f"  {d.name:<20} {sc:<40} {done}/{total} done  (active: {cur})")


# ---- Legacy query mode (backward-compatible) ----

def query_phase(phase: str, mode: str, category: str | None, json_out: bool) -> None:
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
    limit = MODE_LIMITS[mode]
    by_cat: dict[str, list[dict]] = {}
    for a in phase_agents:
        by_cat.setdefault(a["category"], []).append(a)
    print(f"NEXUS Phase {phase} — {PHASE_LABELS[phase]} ({mode.title()} Mode)")
    print("=" * 55)
    n = 0
    for cat in sorted(by_cat):
        print(f"\n  [{cat}]  ({len(by_cat[cat])} agents)")
        for a in by_cat[cat]:
            if n >= limit: break
            print(f"    - {a['name']}")
            n += 1
        if n >= limit:
            print(f"\n  ... +{len(phase_agents) - n} more (use --mode full)")
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
    parser.add_argument("--list-projects", action="store_true", help="List all projects")
    parser.add_argument("--report", action="store_true", help="Generate gate report for a project")
    # Legacy query mode
    parser.add_argument("--phase", "-p", choices=["0","1","2","3","4","5","6"], help="Query agents for a phase")
    parser.add_argument("--mode", "-m", choices=["micro","sprint","full"], default="full")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--category", "-c", help="Filter by category")
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
            start_phase(args.project, args.start)
        elif args.gate:
            run_gate(args.project, args.gate)
        elif args.complete:
            complete_phase(args.project, args.complete)
        else:
            show_status(args.project)
        return
    if args.phase:
        query_phase(args.phase, args.mode, args.category, args.json)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
