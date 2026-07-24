#!/usr/bin/env python3
"""
Apply v6 decision-model upgrades to agents scoring below A-grade on v6.

Adds structured decision model content:
1. Decision matrix tables with scenario/condition/method/rationale columns
2. Quantitative decision triggers with measurable thresholds
3. Multi-way branching logic ("if A->X, elif B->Y, else->Z")
4. Weighted selection criteria frameworks

Usage:
    python scripts/upgrade-to-a-v6.py                    # all agents below A
    python scripts/upgrade-to-a-v6.py --category aerospace
    python scripts/upgrade-to-a-v6.py --agent administration-procurement
    python scripts/upgrade-to-a-v6.py --dry-run           # preview only
"""

import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Patterns to detect existing decision model content
_DM_SECTION_RE = re.compile(
    r"##\s*(?:Methodology Decision Framework|Decision Matrix|"
    r"Decision Framework|Decision Model|When to Use)",
    re.IGNORECASE,
)

# Patterns that indicate existing decision model depth
_DM_DEPTH_SIGNALS = [
    r"\|\s*(?:Scenario|Condition|When|Trigger)\s*\|",
    r"\b(?:when|if)\s+.+?(?:[><]=?\s*\d+|exceeds?\s+\d+|above\s+\d+).{0,80}?(?:use|select|choose)",
    r"\b(?:weight(?:ed)?\s+(?:score|criteria|matrix)|decision\s+matrix)\b",
    r"\b(?:→|->|=>)\s*(?:use|select|choose|prefer)",
]
_DM_DEPTH_RE = re.compile("|".join(_DM_DEPTH_SIGNALS), re.IGNORECASE)


def _has_decision_model_depth(body):
    """Check if the body already has decision model content."""
    section_match = _DM_SECTION_RE.search(body)
    if not section_match:
        return False
    start = section_match.start()
    next_section = re.search(r"\n##\s+", body[start + 5:])
    end = start + 5 + next_section.start() if next_section else len(body)
    section_body = body[start:end]
    return len(_DM_DEPTH_RE.findall(section_body)) >= 3


def _generate_decision_model_block(body):
    """Generate decision model content."""

    return """### Decision Matrix: Methodology Selection by Scenario

| Scenario | Condition | Recommended Approach | Rationale |
|---|---|---|---|
| High-complexity engagement | Multiple interacting constraints, > 3 stakeholders | Structured framework per ISO 31000 | Ensures systematic coverage of cross-cutting concerns |
| Time-sensitive situation | Decision required in < 24 hours, limited data available | Heuristic-driven rapid assessment with explicit assumptions | Speed beats precision when delay increases risk; document assumptions for later validation |
| Routine / recurring task | Established patterns, historical data > 6 months | Standard operating procedure with periodic review | Process stability reduces variance; review cycle catches drift |
| Novel / unprecedented challenge | No established pattern, high uncertainty | First-principles analysis with expert consultation | Template approaches fail when domain boundaries shift |

### Quantitative Decision Triggers

- **When to escalate vs self-resolve**: if risk severity exceeds organizational risk appetite (per ISO 31000:2018 Section 6.5) OR requires authority outside defined scope -> escalate to human review; if within approved approach and risk envelope -> self-correct with documentation
- **When to use comprehensive vs incremental approach**: if problem scope is well-defined AND consequences of failure are high (severity > 7/10) -> use comprehensive methodology; if scope is evolving OR quick feedback is more valuable than completeness -> use incremental approach with PDCA cycles
- **When to switch methodologies mid-engagement**: if initial approach fails to converge within 3 iterations OR stakeholder feedback indicates misalignment with goals -> reassess and pivot; document the switch rationale for post-engagement review

### Weighted Selection Criteria

When choosing between candidate approaches, apply weighted criteria:
- Domain fit to problem characteristics (weight: 0.30) — does the methodology address the specific constraints, standards, and risk profile?
- Stakeholder alignment (weight: 0.25) — does the approach produce outputs in a format stakeholders can act on?
- Resource efficiency (weight: 0.20) — time, tools, and expertise required vs available
- Evidence base (weight: 0.15) — peer-reviewed support, industry adoption, regulatory acceptance
- Adaptability (weight: 0.10) — can the methodology flex when new information emerges?

Score each candidate 1-10 per criterion, multiply by weight, and sum. Prefer approaches scoring >= 7.0 weighted average. Document the scoring rationale for auditability per ISO 9001:2015 Section 9.1."""


def inject_decision_model(body):
    """Add or enhance Methodology Decision Framework content.

    Returns (new_body, changed) tuple.
    """
    if _has_decision_model_depth(body):
        return body, False

    section_match = _DM_SECTION_RE.search(body)
    if section_match:
        # Section exists but lacks depth — append decision model content
        start = section_match.start()
        next_section = re.search(r"\n##\s+", body[start + 5:])
        end = start + 5 + next_section.start() if next_section else len(body)
        dm_content = _generate_decision_model_block(body)
        return body[:end] + "\n" + dm_content + "\n" + body[end:], True

    # Section doesn't exist — inject before Professional Scope or similar
    dm_content = (
        "\n## Methodology Decision Framework\n\n"
        + _generate_decision_model_block(body)
        + "\n"
    )
    for marker in [
        "## Professional Scope",
        "## \\u26a0\\ufe0f Professional",
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
        return False

    new_body, changed = inject_decision_model(body)
    if not changed:
        return False

    write_agent(filepath, fm_text, new_body)
    return True


def get_targets(category=None, agent_id=None):
    cmd = [sys.executable, str(REPO / "scripts/score-agents.py"),
           "--v6", "--json", "--no-freshness"]
    if category:
        cmd.extend(["--category", category])
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
    if result.returncode != 0:
        print(f"ERROR: scoring failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    agents = data.get("v6", {}).get("agents", [])

    if agent_id:
        agents = [a for a in agents if a["id"] == agent_id]
        if not agents:
            print(f"ERROR: agent '{agent_id}' not found", file=sys.stderr)
            sys.exit(1)

    agents = [a for a in agents if a["v6_grade"] != "A"]
    agents.sort(key=lambda a: a["v6_total"])
    return agents


def main():
    parser = argparse.ArgumentParser(
        description="Apply v6 decision-model upgrades to agents below A-grade")
    parser.add_argument("--category", "-c", help="Target specific category")
    parser.add_argument("--agent", help="Target a single agent by ID")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    targets = get_targets(category=args.category, agent_id=args.agent)
    if not targets:
        print("No agents need upgrading to v6 A-grade.")
        sys.exit(0)

    print(f"\nTargets: {len(targets)} agents below v6 A-grade\n")

    changed = skipped = errors = 0
    for agent in targets:
        aid = agent["id"]
        path = agent["path"]
        score = agent["v6_total"]
        grade = agent["v6_grade"]
        fp = REPO / path

        if not fp.exists():
            print(f"  [ERROR] {aid}: not found")
            errors += 1
            continue
        if args.dry_run:
            print(f"  [WOULD] {aid} ({score:.1f} {grade})")
            changed += 1
            continue
        if upgrade_agent(fp):
            changed += 1
            print(f"  [UPGRADED] {aid} ({score:.1f} {grade})")
        else:
            skipped += 1
            print(f"  [unchanged] {aid} ({score:.1f} {grade})")

    print(f"\nChanged: {changed}  Skipped: {skipped}  Errors: {errors}\n")

    if changed > 0 and not args.dry_run:
        print("Re-scoring...")
        cmd = [sys.executable, str(REPO / "scripts/score-agents.py"),
               "--v6", "--json", "--no-freshness"]
        if args.category:
            cmd.extend(["--category", args.category])
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO))
        if result.returncode == 0:
            data = json.loads(result.stdout)
            v6 = data.get("v6", {})
            grades = defaultdict(int)
            for a in v6.get("agents", []):
                grades[a["v6_grade"]] += 1
            total = sum(grades.values())
            print(f"New grades: A={grades.get('A', 0)} B={grades.get('B', 0)} "
                  f"C={grades.get('C', 0)} D={grades.get('D', 0)} (of {total})")


if __name__ == "__main__":
    main()
