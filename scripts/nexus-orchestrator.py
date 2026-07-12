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
        "Market opportunity validated with data?",
        "At least 3 user pain points identified?",
        "Primary sources and key literature collected?",
        "No blocking compliance/regulatory issues?",
        "Problem statement clear and specific?",
    ],
    "1": [
        "Strategy document covers all requirements?",
        "Architecture/outline reviewed and approved?",
        "Work plan with deadlines assigned?",
        "Quality criteria defined for each deliverable?",
        "All stakeholders aligned on scope?",
    ],
    "2": [
        "Infrastructure/tools set up and operational?",
        "Data/sources collected and catalogued?",
        "Templates and standards defined?",
        "Team/environment ready for build phase?",
        "All prerequisites verified as complete?",
    ],
    "3": [
        "All planned tasks completed?",
        "Deliverables match specifications?",
        "Internal review completed?",
        "No critical issues outstanding?",
        "Build artifacts organized and accessible?",
    ],
    "4": [
        "All quality checks passed?",
        "Security/compliance validated?",
        "Performance/correctness verified?",
        "Peer review completed?",
        "Documentation accurate and complete?",
    ],
    "5": [
        "Launch/deployment successful?",
        "Systems stable for 48 hours?",
        "User/client feedback channels operational?",
        "Stakeholders notified?",
        "Support/monitoring active?",
    ],
    "6": [
        "SLO/SLA compliance maintained?",
        "Critical incidents < threshold?",
        "Periodic review completed?",
        "Improvement backlog active?",
        "Metrics trending positively?",
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
    for q in GATE_QUESTIONS[phase]:
        print(f"  ☐ {q}")
    print(f"\nReference: docs/playbooks/phase-{phase}-{PHASE_LABELS[phase].lower()}.md")


def run_gate(name: str, phase: str) -> None:
    cp = load_checkpoint(name)
    ps = cp["phases"][phase]
    if ps["status"] != "in_progress":
        print(f"Phase {phase} is {ps['status']}. Use --start {phase} first.", file=sys.stderr)
        sys.exit(1)
    print(f"\nPhase {phase} — {PHASE_LABELS[phase]}  [GATE CHECK]")
    print("=" * 55)
    print("Answer each (y/n):\n")
    gate = {}
    for q in GATE_QUESTIONS[phase]:
        ans = input(f"  [{q}]  y/n: ").strip().lower()
        gate[q] = ans in ("y", "yes")
        print(f"    {'✓ PASS' if gate[q] else '✗ FAIL'}")
    ps["gate"] = gate
    save_checkpoint(name, cp)
    if all(gate.values()):
        print(f"\nAll passed. Run --complete {phase} to advance.")
    else:
        print(f"\nFailures found. Resolve and re-run --gate {phase}.")


def complete_phase(name: str, phase: str) -> None:
    cp = load_checkpoint(name)
    ps = cp["phases"][phase]
    if ps["status"] != "in_progress":
        print(f"Phase {phase} is {ps['status']}.", file=sys.stderr)
        sys.exit(1)
    if not ps.get("gate") or not all(ps["gate"].values()):
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
        if args.status:
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
