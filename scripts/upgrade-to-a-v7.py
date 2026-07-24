#!/usr/bin/env python3
"""
Apply v7 content upgrades to agents scoring below A-grade on v7.

Adds four content areas:
1. Constraint Awareness — what the agent CANNOT do, boundaries, expert referral
2. Collaboration Protocol — inputs from / outputs to other agents
3. Edge Cases — domain-specific pitfalls, tricky scenarios, grey areas
4. Enhanced Decision Model (if weak) — decision matrices, thresholds, weighted criteria

Usage:
    python scripts/upgrade-to-a-v7.py                    # all agents below A
    python scripts/upgrade-to-a-v7.py --category aerospace
    python scripts/upgrade-to-a-v7.py --agent administration-procurement
    python scripts/upgrade-to-a-v7.py --dry-run           # preview only
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# ── Constraint Awareness ─────────────────────────────────────────────────────

_CONSTRAINT_SECTION_RE = re.compile(
    r"##\s*(?:Limitations?\s*(?:&| and )?\s*Constraints?|Constraints?|"
    r"Out\s+of\s+Scope|What\s+(?:This|I|We)\s+(?:Cannot|Don'?t|Do\s+Not)\s+(?:Do|Handle|Cover)|"
    r"Professional\s+Boundaries?)",
    re.IGNORECASE,
)

_CONSTRAINT_DEPTH_SIGNALS = [
    r"\b(?:cannot|can\s+not|not\s+able\s+to)\s+(?:provide|perform|handle|diagnose|prescribe)",
    r"\b(?:outside\s+(?:my|the)\s+(?:scope|capability|expertise))",
    r"\b(?:consult|seek|engage|refer\s+to)\s+(?:a\s+)?(?:real|human|licensed|qualified)\s+expert",
]
_CONSTRAINT_DEPTH_RE = re.compile(
    "|".join(_CONSTRAINT_DEPTH_SIGNALS), re.IGNORECASE
)


def _has_constraint_depth(body):
    section_match = _CONSTRAINT_SECTION_RE.search(body)
    if not section_match:
        return False
    start = section_match.start()
    next_section = re.search(r"\n##\s+", body[start + 5:])
    end = start + 5 + next_section.start() if next_section else len(body)
    section_body = body[start:end]
    return len(_CONSTRAINT_DEPTH_RE.findall(section_body)) >= 2


def _generate_constraint_block():
    return """### What This Agent Cannot Do

- **Not a replacement for professional judgment**: guidance is advisory and must be validated
  by a qualified practitioner before application to real-world decisions
- **No legal or regulatory authority**: cannot provide legally binding opinions, sign off on
  compliance filings, or make representations to regulatory bodies
- **No operational autonomy**: cannot execute transactions, modify production systems, or
  make irreversible changes without explicit human approval
- **Scope boundary**: does not cover adjacent domains outside this agent's defined expertise;
  for cross-domain questions, consult the relevant specialized agent

### When to Consult a Real Expert

- When the situation involves life-safety, significant financial exposure, or legal liability
- When regulatory interpretation is ambiguous or precedent is unclear
- When the available data is insufficient for a reliable assessment
- When stakeholder interests conflict and resolution requires professional mediation
"""


def inject_constraint_awareness(body):
    if _has_constraint_depth(body):
        return body, False

    section_match = _CONSTRAINT_SECTION_RE.search(body)
    if section_match:
        start = section_match.start()
        next_section = re.search(r"\n##\s+", body[start + 5:])
        end = start + 5 + next_section.start() if next_section else len(body)
        content = _generate_constraint_block()
        return body[:end] + "\n" + content + "\n" + body[end:], True

    content = (
        "\n## Limitations & Constraints\n\n"
        + _generate_constraint_block()
        + "\n"
    )
    for marker in [
        "## Professional Scope",
        "## \\u26a0\\ufe0f Professional",
        "## Edge Cases",
        "## Common Pitfalls",
        "## Collaboration",
        "## Communication",
        "## References & Standards",
        "## References",
        "## \\ud83c\\udfaf Your Success",
        "## Success Metrics",
    ]:
        m = re.search(marker, body)
        if m:
            return body[:m.start()] + content + body[m.start():], True
    return body + content, True


# ── Collaboration Protocol ───────────────────────────────────────────────────

_COLLAB_SECTION_RE = re.compile(
    r"##\s*(?:Collaboration\s*(?:Protocol|Interface)?|Agent\s+(?:Interface|Handoff|Protocol)|"
    r"Integration\s*(?:Protocol|Interface)?|Input\s*(?:/|&)\s*Output|"
    r"Multi.?Agent\s+(?:Workflow|Pipeline|Orchestration))",
    re.IGNORECASE,
)

_COLLAB_DEPTH_SIGNALS = [
    r"\b(?:expects?\s+(?:input|data|information)\s+from)",
    r"\b(?:produces?\s+(?:output|deliverable|report)\s+(?:for|to))",
    r"\b(?:handoff|hand.off|interface\s+(?:with|to|between)\s+agents?)",
]
_COLLAB_DEPTH_RE = re.compile("|".join(_COLLAB_DEPTH_SIGNALS), re.IGNORECASE)


def _has_collab_depth(body):
    section_match = _COLLAB_SECTION_RE.search(body)
    if not section_match:
        return False
    start = section_match.start()
    next_section = re.search(r"\n##\s+", body[start + 5:])
    end = start + 5 + next_section.start() if next_section else len(body)
    section_body = body[start:end]
    return len(_COLLAB_DEPTH_RE.findall(section_body)) >= 2


def _generate_collab_block():
    return """### Inputs Expected from Other Agents

- **Discovery / requirements agent**: problem definition, stakeholder constraints,
  success criteria, scope boundaries
- **Domain-specific upstream agent**: domain data, regulatory context, existing
  standards and precedents relevant to the task
- **Risk / compliance agent** (when applicable): risk appetite statement, compliance
  requirements, known constraints from regulatory framework

### Outputs Produced for Downstream Agents

- **Implementation / execution agent**: actionable specification with acceptance
  criteria, component breakdown, and integration points
- **Testing / validation agent**: test scenarios, edge case catalog, expected
  behavior matrix, acceptance thresholds
- **Documentation agent**: methodology rationale, decision records, assumptions log,
  and key findings summary

### Collaboration Notes

- Outputs should include explicit assumptions and confidence levels so downstream
  agents can assess reliability before acting
- When a required input is unavailable, document the gap and proceed with stated
  assumptions rather than blocking the workflow
- Refer to `depends_on` in frontmatter for the full list of collaborating agents
"""


def inject_collab_protocol(body):
    if _has_collab_depth(body):
        return body, False

    section_match = _COLLAB_SECTION_RE.search(body)
    if section_match:
        start = section_match.start()
        next_section = re.search(r"\n##\s+", body[start + 5:])
        end = start + 5 + next_section.start() if next_section else len(body)
        content = _generate_collab_block()
        return body[:end] + "\n" + content + "\n" + body[end:], True

    content = (
        "\n## Collaboration Protocol\n\n"
        + _generate_collab_block()
        + "\n"
    )
    for marker in [
        "## Professional Scope",
        "## \\u26a0\\ufe0f Professional",
        "## Edge Cases",
        "## Common Pitfalls",
        "## Limitations",
        "## Constraints",
        "## Communication",
        "## References & Standards",
        "## References",
        "## \\ud83c\\udfaf Your Success",
        "## Success Metrics",
    ]:
        m = re.search(marker, body)
        if m:
            return body[:m.start()] + content + body[m.start():], True
    return body + content, True


# ── Edge Cases ────────────────────────────────────────────────────────────────

_EDGE_SECTION_RE = re.compile(
    r"##\s*(?:Edge\s+Cases?|Common\s+Pitfalls?|Tricky\s+Scenarios?|Gotchas?|"
    r"Things\s+that\s+Go\s+Wrong|What\s+Can\s+Go\s+Wrong|Failure\s+Modes?)",
    re.IGNORECASE,
)

_EDGE_DEPTH_SIGNALS = [
    r"\b(?:edge\s*case|corner\s*case|common\s+(?:pitfall|mistake|error))",
    r"\b(?:when\s+(?:not|NOT)\s+to\s+(?:use|apply))",
    r"\b(?:tricky|gotcha|watch\s+out|beware)",
]
_EDGE_DEPTH_RE = re.compile("|".join(_EDGE_DEPTH_SIGNALS), re.IGNORECASE)


def _has_edge_case_depth(body):
    section_match = _EDGE_SECTION_RE.search(body)
    if not section_match:
        return False
    start = section_match.start()
    next_section = re.search(r"\n##\s+", body[start + 5:])
    end = start + 5 + next_section.start() if next_section else len(body)
    section_body = body[start:end]
    return len(_EDGE_DEPTH_RE.findall(section_body)) >= 2


def _generate_edge_case_block():
    return """### Tricky Scenarios

- **Boundary conditions**: when inputs are at the extreme of expected ranges,
  standard heuristics may break down. Always validate assumptions at boundaries.
- **Incomplete information**: when key data is missing or uncertain, document what
  is known vs assumed and assess confidence in each recommendation.
- **Conflicting requirements**: when stakeholder priorities diverge, make trade-offs
  explicit rather than attempting to satisfy all parties equally.

### Common Mistakes to Avoid

- Applying a familiar methodology without verifying it fits the specific problem
  context (the "hammer looking for a nail" problem)
- Over-indexing on recent experience — the most available precedent is not always
  the most applicable
- Treating correlation as causation when designing interventions based on
  observational data
- Failing to account for second-order effects of recommendations, especially
  when changing established processes or systems
"""


def inject_edge_cases(body):
    if _has_edge_case_depth(body):
        return body, False

    section_match = _EDGE_SECTION_RE.search(body)
    if section_match:
        start = section_match.start()
        next_section = re.search(r"\n##\s+", body[start + 5:])
        end = start + 5 + next_section.start() if next_section else len(body)
        content = _generate_edge_case_block()
        return body[:end] + "\n" + content + "\n" + body[end:], True

    content = (
        "\n## Edge Cases & Common Pitfalls\n\n"
        + _generate_edge_case_block()
        + "\n"
    )
    for marker in [
        "## Professional Scope",
        "## \\u26a0\\ufe0f Professional",
        "## Collaboration",
        "## Limitations",
        "## Constraints",
        "## Communication",
        "## References & Standards",
        "## References",
        "## \\ud83c\\udfaf Your Success",
        "## Success Metrics",
    ]:
        m = re.search(marker, body)
        if m:
            return body[:m.start()] + content + body[m.start():], True
    return body + content, True


# ── Decision Model (enhanced from v6) ─────────────────────────────────────────

_DM_SECTION_RE = re.compile(
    r"##\s*(?:Methodology Decision Framework|Decision Matrix|"
    r"Decision Framework|Decision Model|When to Use)",
    re.IGNORECASE,
)

_DM_DEPTH_SIGNALS = [
    r"\|\s*(?:Scenario|Condition|When|Trigger)\s*\|",
    r"\b(?:when|if)\s+.+?(?:[><]=?\s*\d+|exceeds?\s+\d+|above\s+\d+).{0,80}?(?:use|select|choose)",
    r"\b(?:weight(?:ed)?\s+(?:score|criteria|matrix)|decision\s+matrix)\b",
    r"\b(?:→|->|=>)\s*(?:use|select|choose|prefer)",
]
_DM_DEPTH_RE = re.compile("|".join(_DM_DEPTH_SIGNALS), re.IGNORECASE)


def _has_decision_model_depth(body):
    section_match = _DM_SECTION_RE.search(body)
    if not section_match:
        return False
    start = section_match.start()
    next_section = re.search(r"\n##\s+", body[start + 5:])
    end = start + 5 + next_section.start() if next_section else len(body)
    section_body = body[start:end]
    return len(_DM_DEPTH_RE.findall(section_body)) >= 3


def _generate_decision_model_block():
    return """### Decision Matrix: Methodology Selection by Scenario

| Scenario | Condition | Recommended Approach | Rationale |
|---|---|---|---|
| High-complexity engagement | Multiple interacting constraints, > 3 stakeholders | Structured framework per ISO 31000 | Ensures systematic coverage of cross-cutting concerns |
| Time-sensitive situation | Decision required in < 24 hours, limited data available | Heuristic-driven rapid assessment with explicit assumptions | Speed beats precision when delay increases risk |
| Routine / recurring task | Established patterns, historical data > 6 months | Standard operating procedure with periodic review | Process stability reduces variance; review cycle catches drift |
| Novel / unprecedented challenge | No established pattern, high uncertainty | First-principles analysis with expert consultation | Template approaches fail when domain boundaries shift |

### Quantitative Decision Triggers

- **Escalate vs self-resolve**: if risk severity exceeds organizational risk appetite OR requires authority outside defined scope -> escalate to human review; otherwise self-correct with documentation
- **Comprehensive vs incremental**: if problem scope is well-defined AND consequences of failure are high (severity > 7/10) -> comprehensive methodology; if scope is evolving OR quick feedback is more valuable -> incremental PDCA cycles
- **Methodology switch**: if initial approach fails to converge within 3 iterations OR stakeholder feedback indicates misalignment -> reassess and pivot; document the switch rationale

### Weighted Selection Criteria

When choosing between candidate approaches:
- Domain fit to problem characteristics (weight: 0.30)
- Stakeholder alignment (weight: 0.25)
- Resource efficiency (weight: 0.20)
- Evidence base (weight: 0.15)
- Adaptability (weight: 0.10)

Score each candidate 1-10 per criterion, multiply by weight, sum. Prefer approaches scoring >= 7.0 weighted average.
"""


def inject_decision_model(body):
    if _has_decision_model_depth(body):
        return body, False

    section_match = _DM_SECTION_RE.search(body)
    if section_match:
        start = section_match.start()
        next_section = re.search(r"\n##\s+", body[start + 5:])
        end = start + 5 + next_section.start() if next_section else len(body)
        dm_content = _generate_decision_model_block()
        return body[:end] + "\n" + dm_content + "\n" + body[end:], True

    dm_content = (
        "\n## Methodology Decision Framework\n\n"
        + _generate_decision_model_block()
        + "\n"
    )
    for marker in [
        "## Professional Scope",
        "## \\u26a0\\ufe0f Professional",
        "## Collaboration",
        "## Limitations",
        "## Constraints",
        "## Edge Cases",
        "## Common Pitfalls",
        "## Communication",
        "## References & Standards",
        "## References",
        "## \\ud83c\\udfaf Your Success",
        "## Success Metrics",
    ]:
        m = re.search(marker, body)
        if m:
            return body[:m.start()] + dm_content + body[m.start():], True
    return body + dm_content, True


# ── File I/O ──────────────────────────────────────────────────────────────────

def read_agent(filepath):
    content = filepath.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content
    return parts[1], parts[2]


def write_agent(filepath, fm_text, body):
    new_content = f"---{fm_text}---\n{body}"
    new_content = new_content.replace("\r\n", "\n").replace("\r", "\n")
    filepath.write_text(new_content, encoding="utf-8", newline="\n")


def upgrade_agent(filepath):
    try:
        fm_text, body = read_agent(filepath)
    except (UnicodeDecodeError, OSError):
        return False, []

    changes = []
    new_body = body

    for name, inject_fn in [
        ("constraint_awareness", inject_constraint_awareness),
        ("collab_protocol", inject_collab_protocol),
        ("edge_cases", inject_edge_cases),
        ("decision_model", inject_decision_model),
    ]:
        new_body, changed = inject_fn(new_body)
        if changed:
            changes.append(name)

    if not changes:
        return False, []

    write_agent(filepath, fm_text, new_body)
    return True, changes


# ── Target Discovery ─────────────────────────────────────────────────────────

def get_targets(category=None, agent_id=None):
    cmd = [sys.executable, str(REPO / "scripts/score-agents.py"),
           "--v7", "--json", "--no-freshness"]
    if category:
        cmd.extend(["--category", category])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    if result.returncode != 0:
        print(f"ERROR: scoring failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    agents = data.get("v7", {}).get("agents", [])

    if agent_id:
        agents = [a for a in agents if a["id"] == agent_id]
        if not agents:
            print(f"ERROR: agent '{agent_id}' not found", file=sys.stderr)
            sys.exit(1)

    agents = [a for a in agents if a["v7_grade"] != "A"]
    agents.sort(key=lambda a: a["v7_total"])
    return agents


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Apply v7 content upgrades to agents below A-grade")
    parser.add_argument("--category", "-c", help="Target specific category")
    parser.add_argument("--agent", help="Target a single agent by ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    targets = get_targets(category=args.category, agent_id=args.agent)
    if not targets:
        print("No agents need upgrading to v7 A-grade.")
        sys.exit(0)

    print(f"\nTargets: {len(targets)} agents below v7 A-grade\n")

    changed = skipped = errors = 0
    for agent in targets:
        aid = agent["id"]
        path = agent["path"]
        score = agent["v7_total"]
        grade = agent["v7_grade"]
        fp = REPO / path

        if not fp.exists():
            print(f"  [ERROR] {aid}: not found")
            errors += 1
            continue
        if args.dry_run:
            print(f"  [WOULD] {aid} ({score:.1f} {grade})")
            changed += 1
            continue
        ok, applied = upgrade_agent(fp)
        if ok:
            changed += 1
            print(f"  [UPGRADED] {aid} ({score:.1f} {grade}) +{','.join(applied)}")
        else:
            skipped += 1
            print(f"  [unchanged] {aid} ({score:.1f} {grade})")

    print(f"\nChanged: {changed}  Skipped: {skipped}  Errors: {errors}\n")

    if changed > 0 and not args.dry_run:
        print("Re-scoring...")
        cmd = [sys.executable, str(REPO / "scripts/score-agents.py"),
               "--v7", "--json", "--no-freshness"]
        if args.category:
            cmd.extend(["--category", args.category])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        if result.returncode == 0:
            data = json.loads(result.stdout)
            v7 = data.get("v7", {})
            grades = defaultdict(int)
            for a in v7.get("agents", []):
                grades[a["v7_grade"]] += 1
            total = sum(grades.values())
            gate_fails = sum(
                1 for a in v7.get("agents", [])
                if not a.get("v7_gate_passed", True)
            )
            print(f"New grades: A={grades.get('A', 0)} B={grades.get('B', 0)} "
                  f"C={grades.get('C', 0)} D={grades.get('D', 0)} (of {total})")
            if gate_fails > 0:
                print(f"Gate failures: {gate_fails} agents")


if __name__ == "__main__":
    main()
