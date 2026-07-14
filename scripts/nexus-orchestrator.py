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
    "enterprise-feature": {
        "name": "Enterprise Feature Development",
        "duration": "6-12 weeks", "agents": "20-30",
        "phases": ["0", "1", "2", "3", "4"],
        "phase_labels": {
            "0": "Requirements & Architecture",
            "1": "Foundation",
            "2": "Build",
            "3": "Hardening",
            "4": "Rollout",
        },
        "feedback": {"3": "2", "4": "2"},
        "runbook": "docs/runbooks/scenario-enterprise-feature.md",
    },
    "incident-response": {
        "name": "Incident Response",
        "duration": "Minutes to hours", "agents": "3-8",
        "phases": ["0", "1", "2", "3"],
        "phase_labels": {
            "0": "Detection & Triage",
            "1": "Containment",
            "2": "Resolution",
            "3": "Post-Mortem",
        },
        "feedback": {},
        "runbook": "docs/runbooks/scenario-incident-response.md",
    },
    "marketing-campaign": {
        "name": "Multi-Channel Marketing Campaign",
        "duration": "2-4 weeks", "agents": "10-15",
        "phases": ["0", "1", "2", "3"],
        "phase_labels": {
            "0": "Strategy & Content",
            "1": "Launch & Activate",
            "2": "Optimize & Sustain",
            "3": "Report & Learn",
        },
        "feedback": {"2": "0"},
        "runbook": "docs/runbooks/scenario-marketing-campaign.md",
    },
}

GATE_QUESTIONS = {
    "default": {
        "0": [
            ("Market opportunity validated?", "Threshold: TAM > minimum viable | Evidence: Trend Researcher report with sources | Describe data supporting market demand."),
            ("User need confirmed?", "Threshold: >=3 validated pain points | Evidence: Feedback Synthesizer + UX Researcher data | List pain points with sources."),
            ("Regulatory path clear?", "Threshold: No blocking compliance issues | Evidence: Legal Compliance Checker matrix | Note any issues or N/A status."),
            ("Data foundation assessed?", "Threshold: Key metrics identified | Evidence: Analytics Reporter audit | Confirm baseline data available."),
            ("Tech feasibility confirmed?", "Threshold: Stack validated | Evidence: Tool Evaluator assessment | All components have implementation path?"),
        ],
        "1": [
            ("Strategy covers all requirements?", "Threshold: 100% spec coverage | Evidence: Senior PM task list cross-referenced | No gaps in implementation plan."),
            ("Architecture approved?", "Threshold: All components have implementation path | Evidence: Backend Architect + UX Architect specs | Who reviewed and approved?"),
            ("Brand system complete?", "Threshold: Logo, colors, typography, voice defined | Evidence: Brand Guardian deliverable | All brand elements ready?"),
            ("Budget approved?", "Threshold: Within organizational constraints | Evidence: Finance Tracker plan with ROI projections | Budget greenlit?"),
            ("Sprint plan realistic?", "Threshold: Velocity-based estimation | Evidence: Sprint Prioritizer backlog with dependency map | Timelines achievable?"),
            ("Security architecture defined?", "Threshold: Threat model + security controls documented | Evidence: Backend Architect + Security review | Security covered?"),
        ],
        "2": [
            ("CI/CD pipeline operational?", "Threshold: Pipeline running end-to-end | Evidence: Pipeline execution logs | Build + test + deploy verified."),
            ("Database schema deployed?", "Threshold: All migrations applied | Evidence: Migration success + schema dump | Tables/indexes created?"),
            ("API scaffold responding?", "Threshold: Health checks live (HTTP 200) | Evidence: curl response screenshots | Endpoints reachable?"),
            ("Frontend rendering?", "Threshold: App loads without errors | Evidence: Evidence Collector screenshots | Skeleton app functional?"),
            ("Monitoring active?", "Threshold: Dashboards live | Evidence: Grafana/monitoring screenshots | Real-time metrics visible?"),
        ],
        "3": [
            ("All tasks pass QA?", "Threshold: 100% task completion with PASS | Evidence: Evidence Collector per-task verification | Any outstanding items?"),
            ("API endpoints validated?", "Threshold: All endpoints tested | Evidence: API Tester report | Full regression passing?"),
            ("Performance baselines met?", "Threshold: P95 < 200ms, LCP < 2.5s | Evidence: Performance Benchmarker report | Meet or exceed targets?"),
            ("Brand consistency verified?", "Threshold: 95%+ adherence | Evidence: Brand Guardian audit | Visual consistency across all views?"),
            ("No critical bugs?", "Threshold: Zero P0/P1 open | Evidence: Test Results Analyzer summary | All known issues addressed?"),
            ("Code review completed?", "Threshold: All PRs reviewed + approved | Evidence: Code review logs | Merge blockers resolved?"),
        ],
        "4": [
            ("User journeys complete?", "Threshold: All critical paths working | Evidence: End-to-end screenshots | Desktop + Tablet + Mobile verified?"),
            ("Cross-device consistency?", "Threshold: 3 device sizes verified | Evidence: Responsive screenshots | Layout consistent across breakpoints?"),
            ("Security validated?", "Threshold: Zero critical vulnerabilities | Evidence: Security scan report | All findings addressed?"),
            ("Compliance certified?", "Threshold: All regulatory requirements met | Evidence: Legal Compliance Checker report | Any outstanding items?"),
            ("Infrastructure ready?", "Threshold: Production environment validated | Evidence: Infrastructure Maintainer report | Scaled and stable?"),
            ("Specification compliance?", "Threshold: 100% spec verified | Evidence: Reality Checker point-by-point verification | Every requirement met?"),
        ],
        "5": [
            ("Deployment successful?", "Threshold: Zero-downtime, all health checks pass | Evidence: DevOps deployment logs | Any rollback or errors?"),
            ("Systems stable for 48h?", "Threshold: No P0/P1 in first 48 hours | Evidence: Infrastructure monitoring | Error rates normal?"),
            ("User acquisition active?", "Threshold: Traffic > baseline | Evidence: Analytics Reporter dashboard | Channels driving traffic?"),
            ("Feedback loop operational?", "Threshold: Feedback channels active | Evidence: Feedback Synthesizer report | User feedback being collected?"),
            ("Support operational?", "Threshold: Response time < 1h | Evidence: Support dashboard | Customer issues being resolved?"),
        ],
        "6": [
            ("SLO compliance maintained?", "Threshold: SLO targets met | Evidence: SLO/SLA compliance data | Any breaches this period?"),
            ("Incidents under threshold?", "Threshold: Trend stable or ↓ | Evidence: Incident count + trend report | P0/P1/P2 count vs previous?"),
            ("Periodic review done?", "Threshold: Review cadence met | Evidence: Review meeting notes | Key findings documented?"),
            ("Improvement backlog active?", "Threshold: Items tracked with owner | Evidence: Backlog status report | Top items progressing?"),
            ("Metrics positive?", "Threshold: Metrics trending ↑ | Evidence: KPI dashboard | Key metrics direction for the period?"),
        ],
    },
    "incident-response": {
        "0": [
            ("Alert acknowledged immediately?", "Who acknowledged and when (timestamp)?"),
            ("Scope and impact assessed?", "How many users/systems affected? Estimated blast radius."),
            ("Severity level classified?", "P0/P1/P2/P3 — based on the incident response runbook."),
            ("Response team activated?", "Which agents mobilized? IC assigned?"),
            ("Stakeholder comms initiated?", "Status page updated? Executive notified?"),
        ],
        "1": [
            ("Containment applied?", "Rollback, feature flag off, or traffic drained?"),
            ("User impact stopped?", "Confirm error rates, latency, and availability back to baseline."),
            ("Customer comms sent?", "Status page updated with containment ETA?"),
            ("Incident log started?", "Timeline doc created with key events?"),
        ],
        "2": [
            ("Root cause identified?", "What was the underlying cause (not just the symptom)?"),
            ("Fix deployed and verified?", "Evidence of fix in production with metrics confirming resolution."),
            ("No regressions detected?", "Full regression suite passed? Canary metrics clean?"),
            ("Post-incident status posted?", "Status page shows 'resolved' with summary?"),
        ],
        "3": [
            ("Incident timeline documented?", "Full timeline with timestamps for all key events?"),
            ("Root cause analysis complete?", "5-Whys or similar? Contributing factors identified?"),
            ("Action items created and assigned?", "Each with owner and due date?"),
            ("Post-mortem review scheduled?", "Date set for review with relevant teams?"),
            ("Prevention plan documented?", "What changes prevent this class of incident?"),
        ],
    },
    "marketing-campaign": {
        "0": [
            ("Campaign objectives defined?", "Clear KPIs for reach, engagement, conversion?"),
            ("Content calendar complete?", "All platforms scheduled with publish dates?"),
            ("Brand guidelines reviewed?", "Brand Guardian signed off on campaign assets?"),
            ("Compliance check done?", "Ad disclosures, platform policies verified?"),
            ("Analytics tracking configured?", "UTM parameters, conversion events set up?"),
        ],
        "1": [
            ("All content published on schedule?", "Any delays or blockers in the launch sequence?"),
            ("Engagement tracking live?", "Real-time dashboard showing metrics per platform?"),
            ("A/B tests running?", "Test variants active and collecting data?"),
            ("Team responding to engagement?", "Comments, replies, DMs handled within SLA?"),
            ("First 48h snapshot taken?", "Early performance data captured for comparison?"),
        ],
        "2": [
            ("Performance data analyzed?", "Which channels over/under-performing?"),
            ("Channel optimization applied?", "Budget reallocation based on ROAS data?"),
            ("New content created from data?", "Response content based on top-performing themes?"),
            ("Weekly report delivered?", "Campaign status shared with stakeholders?"),
        ],
        "3": [
            ("Comprehensive campaign analysis done?", "Full funnel: reach → engagement → conversion?"),
            ("ROI calculated?", "Total spend vs. return by channel?"),
            ("Lessons documented?", "What worked, what didn't, and recommendations?"),
            ("Executive summary delivered?", "C-suite brief with key takeaways and next steps?"),
            ("Follow-up campaign plan ready?", "Nurture sequences or next campaign drafted?"),
        ],
    },
}


def get_gate_questions(scenario: str, phase: str) -> list[tuple[str, str]]:
    """Return gate questions for a specific scenario and phase, falling back to default."""
    questions = GATE_QUESTIONS.get(scenario, {})
    if phase in questions:
        return questions[phase]
    return GATE_QUESTIONS["default"].get(phase, [])

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
    for q, desc in get_gate_questions(cp["scenario"], phase):
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
    for question, desc in get_gate_questions(cp["scenario"], phase):
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


SCENARIO_KEYWORDS = {
    "software": ["software", "product", "app", "mvp", "web", "api", "saas", "feature", "build", "develop", "startup", "platform", "mobile", "fullstack", "deploy", "软件", "产品", "开发", "应用", "平台", "构建", "部署"],
    "enterprise-feature": ["enterprise", "compliance", "security", "stakeholder", "existing", "integration", "governance", "regulatory", "audit", "corporate", "legacy", "migration", "企业", "合规", "安全", "审计", "监管", "迁移", "集成"],
    "research": ["research", "report", "paper", "white paper", "analysis", "study", "market", "data", "investigation", "survey", "findings", "literature", "研究", "报告", "分析", "调研", "论文", "白皮书", "调查", "数据"],
    "consulting": ["consulting", "strategy", "engagement", "client", "advisory", "framework", "recommendation", "assessment", "diagnostic", "roadmap", "maturity", "咨询", "战略", "建议", "评估", "框架", "路线图", "客户"],
    "education": ["course", "curriculum", "education", "training", "learning", "teach", "lesson", "module", "cohort", "syllabus", "pedagogy", "assessment", "课程", "教育", "培训", "教学", "学习", "课件"],
    "marketing-campaign": ["marketing", "campaign", "content", "social media", "launch", "brand", "ads", "promotion", "seo", "email", "growth", "acquisition", "engagement", "funnel", "营销", "推广", "品牌", "广告", "活动", "增长", "内容"],
    "incident-response": ["incident", "outage", "bug", "broken", "emergency", "p0", "alert", "downtime", "breach", "attack", "fire", "triage", "resolution", "postmortem", "post-mortem", "root cause", "故障", "事故", "宕机", "紧急", "报警", "恢复", "复盘"],
}


def discover_scenario(query: str) -> None:
    """Help users discover the right NEXUS scenario for their project."""
    query_lower = query.lower()
    scores: dict[str, int] = {}
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in query_lower:
                score += len(kw)  # longer keyword matches count more
        if score > 0:
            scores[scenario] = score

    print(f"\nNEXUS Scenario Discovery for: \"{query}\"\n")
    print(f"{'Scenario':<25} {'Match':<8} {'Phases':<8} {'Duration':<20}")
    print("-" * 65)

    if not scores:
        print("  No direct matches. Try different keywords.\n")
        print("Available scenarios:")
        for name, sc in SCENARIOS.items():
            print(f"  --scenario {name:<20} → {sc['name']} ({sc['duration']})")
        return

    for scenario, score in sorted(scores.items(), key=lambda x: -x[1]):
        sc = SCENARIOS[scenario]
        bar = "█" * min(score // 3, 10)
        phases_str = " → ".join(sc["phases"])
        print(f"  --scenario {scenario:<14} {bar:<8} {phases_str:<8} {sc['duration']:<20}")

    best = max(scores, key=scores.get)
    sc = SCENARIOS[best]
    print(f"\nTop match: --scenario {best} ({sc['name']})")
    print(f"  Duration: {sc['duration']}  |  Agents: {sc['agents']}")
    print(f"  Runbook: {sc['runbook']}")
    print(f"\nNext: python scripts/nexus-orchestrator.py --init <name> --scenario {best}")

def nexus_stats() -> None:
    """Show NEXUS-wide statistics."""
    agents = load_agents()
    phase_counts: dict[str, int] = {}
    for a in agents:
        for r in (a.get("nexus_roles") or []):
            phase_counts[r] = phase_counts.get(r, 0) + 1

    unique_cats = len({a["category"] for a in agents})

    print("\nNEXUS Statistics")
    print("=" * 55)
    print(f"  Agents:       {len(agents)}")
    print(f"  Categories:   {unique_cats}")

    print("\nPhase Distribution:")
    for p in sorted(phase_counts.keys()):
        label = PHASE_LABELS.get(p.split("-")[1], p)
        bar = "█" * (phase_counts[p] // 20)
        print(f"  {p} ({label:<12}): {phase_counts[p]:>4} {bar}")

    print("\nProjects:")
    if not PROJECTS_DIR.exists():
        print("  No projects directory")
        return
    projects = list(PROJECTS_DIR.glob("*/checkpoint.json"))
    if not projects:
        print("  No projects yet. Create with --init <name>")
        return
    print(f"  Total projects: {len(projects)}")
    scenarios_used: dict[str, int] = {}
    for cp_file in projects:
        cp = json.loads(cp_file.read_text(encoding="utf-8"))
        sc = cp.get("scenario", "unknown")
        scenarios_used[sc] = scenarios_used.get(sc, 0) + 1
        done = sum(1 for p in cp["phases"].values() if p["status"] == "completed")
        total = len(cp["phases"])
        print(f"    {cp_file.parent.name:<20} {sc:<25} {done}/{total} complete")

    print("\nScenario Usage:")
    for sc, count in sorted(scenarios_used.items(), key=lambda x: -x[1]):
        name = SCENARIOS.get(sc, {}).get("name", sc)
        print(f"  {sc:<25} {count} project(s) — {name}")


def export_project(name: str, output_path: str | None = None) -> None:
    """Export project checkpoint as JSON."""
    cp = load_checkpoint(name)
    if output_path:
        Path(output_path).write_text(
            json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Exported {name} to {output_path}")
    else:
        print(json.dumps(cp, ensure_ascii=False, indent=2))

def preview_scenario(scenario: str) -> None:
    """Show scenario details without creating a project."""
    sc = SCENARIOS.get(scenario)
    if not sc:
        print(f"Unknown scenario: {scenario}", file=sys.stderr)
        print(f"Available: {', '.join(SCENARIOS)}", file=sys.stderr)
        sys.exit(1)

    agents = load_agents()
    phase_summary = []
    for p in sc["phases"]:
        label = sc["phase_labels"].get(p, PHASE_LABELS.get(p, f"Phase {p}"))
        count = len(filter_by_phase(agents, p))
        phase_summary.append(f"P{p} {label} ({count} agents)")

    fb = get_feedback_loops(scenario)

    print(f"\n{sc['name']}")
    print("=" * 55)
    print(f"  Duration:    {sc['duration']}")
    print(f"  Agents:      {sc['agents']}")
    print(f"  Runbook:     {sc['runbook']}")
    print(f"\n  Phases ({len(sc['phases'])}):")
    for ps in phase_summary:
        print(f"    {ps}")
    if fb:
        print("\n  Feedback Loops:")
        for from_p, to_p in sorted(fb.items()):
            fl = get_phase_label(scenario, from_p)
            tl = get_phase_label(scenario, to_p)
            print(f"    {fl} (P{from_p}) --found issues--> {tl} (P{to_p})")
    print(f"\n  Create: python scripts/nexus-orchestrator.py --init <name> --scenario {scenario}")


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

def query_phase(phase: str, mode: str, category: str | None, json_out: bool, verbose: bool = False, scenario: str = "software") -> None:
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
    label = get_phase_label(scenario, phase)
    print(f"NEXUS Phase {phase} — {label} ({mode.title()} Mode)")
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
    parser.add_argument("--preview", choices=list(SCENARIOS), help="Preview a scenario without creating a project")
    parser.add_argument("--discover", help="Discover the right scenario for your project (e.g. 'launch a mobile app')")
    parser.add_argument("--list-projects", action="store_true", help="List all projects")
    parser.add_argument("--report", action="store_true", help="Generate gate report for a project")
    # Legacy query mode
    parser.add_argument("--phase", "-p", choices=["0","1","2","3","4","5","6"], help="Query agents for a phase")
    parser.add_argument("--mode", "-m", choices=["micro","sprint","full"], default="full")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--category", "-c", help="Filter by category")
    parser.add_argument("--export", help="Export project checkpoint as JSON (optional: --out PATH)")
    parser.add_argument("--out", help="Output path for --export")
    parser.add_argument("--stats", action="store_true", help="Show NEXUS-wide statistics")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full agent listing")
    args = parser.parse_args()

    if args.preview:
        preview_scenario(args.preview)
        return
    if args.stats:
        nexus_stats()
        return
    if args.discover:
        discover_scenario(args.discover)
        return
    if args.list_projects:
        list_projects()
        return
    if args.init:
        init_project(args.init, args.scenario)
        return
    if args.export:
        export_project(args.export, args.out)
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
        query_phase(args.phase, args.mode, args.category, args.json, verbose=args.verbose, scenario=args.scenario)
        return
    parser.print_help()


if __name__ == "__main__":
    main()
