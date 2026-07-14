#!/usr/bin/env python
"""Agent content expansion helper — bridges B-grade agents to A-grade.

Analyzes an underweight agent, finds the best A-grade agents in the same
category as structural templates, and generates a concrete expansion plan
with section-by-section word targets and template snippets.

Usage:
    python scripts/expand-agent.py manufacturing-engineering-electronics-manufacturing
    python scripts/expand-agent.py --category manufacturing --all-below 400
    python scripts/expand-agent.py --agent agent-id --dry-run     # preview only
    python scripts/expand-agent.py --agent agent-id --output-dir expanded/
"""

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from _shared import BOLD, CYAN, GREEN, RED, RESET, YELLOW, discover_agents, get_body, load_module

_SCRIPTS = Path(__file__).resolve().parent
_score_agents = load_module("score_agents", _SCRIPTS / "score-agents.py")
CORE_SECTIONS = _score_agents.CORE_SECTIONS
score_agent = _score_agents.score_agent

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

# Sections that add substance to an agent (beyond the generic scaffold)
EXPANSION_SECTIONS = {
    "Identity & Backstory": {
        "priority": 1,
        "target_words": 80,
        "description": "Give your agent a persona name, years of experience, and a narrative backstory",
        "template": """## 🧠 Your Identity & Memory

You are **[Persona Name]**, a [role] with [X]+ years of experience in [domain]. You've [key accomplishment 1], [key accomplishment 2], and learned that [key insight].

You think in **[core concepts]**. [Domain] answers: [key question 1]? [key question 2]? [key question 3]?

**You remember and carry forward:**
- [Domain knowledge bullet 1 — a key principle or methodology]
- [Domain knowledge bullet 2 — a common pitfall and how to avoid it]
- [Domain knowledge bullet 3 — a metric or framework you use to evaluate situations]""",
    },
    "Success Metrics": {
        "priority": 2,
        "target_words": 60,
        "description": "Define 4-5 measurable KPIs your agent tracks",
        "template": """## 🎯 Your Success Metrics

- **[Metric 1]** — [what it measures and what good looks like]
- **[Metric 2]** — [what it measures and what good looks like]
- **[Metric 3]** — [what it measures and what good looks like]
- **[Metric 4]** — [what it measures and what good looks like]
- **[Metric 5]** — [what it measures and what good looks like]""",
    },
    "Communication Style": {
        "priority": 3,
        "target_words": 60,
        "description": "Define how your agent communicates — tone, format, audience adaptation",
        "template": """## 💬 Your Communication Style

- **[Style trait 1]**: [how you apply this in responses]
- **[Style trait 2]**: [how you apply this in responses]
- **[Style trait 3]**: [how you apply this in responses]
- **[Style trait 4]**: [how you apply this in responses]
- **[Style trait 5]**: [how you apply this in responses]""",
    },
    "Instructions Reference": {
        "priority": 4,
        "target_words": 40,
        "description": "A condensed summary of your methodology for quick reference",
        "template": """---

**Instructions Reference**: Your [domain] methodology is built on [X]+ years of [field]. [Principle 1], [principle 2], [principle 3], and [principle 4].""",
    },
    "Critical Rules Enhancement": {
        "priority": 5,
        "target_words": 80,
        "description": "Expand generic rules with domain-specific, actionable guidelines",
        "template": """## 🚨 Critical Rules You Must Follow

1. **Stay in your domain.** Provide advice only within your area of expertise.
2. **Be specific and actionable.** Every recommendation must include concrete steps.
3. **[Domain-specific rule 1]**: [detailed explanation of a rule unique to your field]
4. **[Domain-specific rule 2]**: [detailed explanation of a rule unique to your field]
5. **[Domain-specific rule 3]**: [detailed explanation of a rule unique to your field]""",
    },
}


def find_reference_agents(category, agent_id, top_n=3):
    """Find the best A-grade agents in the same category to use as templates."""
    candidates = []
    for _cat, _rel, filepath in discover_agents(category_filter=category):
        if filepath.stem == agent_id:
            continue
        result = score_agent(filepath, check_freshness=False)
        if result["grade"] == "A" and result["word_count"] >= 400:
            candidates.append((result["word_count"], result["total"], result["id"], filepath))

    candidates.sort(key=lambda x: (-x[1], -x[0]))
    return candidates[:top_n]


def analyze_expansion_needs(agent_id, category, filepath):
    """Analyze what an agent needs to reach A-grade."""
    result = score_agent(filepath, check_freshness=False)
    scores = result["scores"]

    needs = []
    word_budget = 0

    # Check each dimension
    if scores["content_depth"] < 3:
        gap = 800 - result["word_count"]
        if gap > 0:
            needs.append({
                "dimension": "content_depth",
                "current": result["word_count"],
                "target": "400+ (for score 2) or 800+ (for score 3)",
                "gap_words": max(0, 400 - result["word_count"]),
                "priority": 1,
            })
            word_budget += max(0, 400 - result["word_count"])

    if scores["structure"] < 3:
        # Find which specific sections are missing
        body = get_body(filepath.read_text(encoding="utf-8"))
        missing = []
        for section, pattern in CORE_SECTIONS.items():
            import re
            if not re.search(pattern, body, re.IGNORECASE):
                missing.append(section)
        needs.append({
            "dimension": "structure",
            "current": f"{result['sections_found']}/7",
            "target": "7/7",
            "missing_sections": missing,
            "priority": 2,
        })
        word_budget += len(missing) * 60

    if scores["frontmatter"] < 2:
        needs.append({
            "dimension": "frontmatter",
            "current": result.get("frontmatter_details", []),
            "target": "description (80+ chars), emoji, color, vibe, nexus_roles",
            "priority": 1,
        })

    if scores["file_health"] < 2:
        needs.append({
            "dimension": "file_health",
            "current": f"{result.get('file_size_kb', 0)} KB",
            "target": "2-8 KB",
            "priority": 3,
        })

    return {
        "agent_id": agent_id,
        "category": category,
        "path": str(filepath),
        "current_grade": result["grade"],
        "current_total": result["total"],
        "current_scores": scores,
        "word_count": result["word_count"],
        "needs": needs,
        "estimated_new_words": word_budget,
        "projected_grade": "A" if result["total"] >= 8 or (result["total"] + min(3, len(needs))) >= 8 else "B",
        "issues": result["issues"],
    }


def generate_expansion_plan(analysis, ref_agents):
    """Generate a section-by-section expansion plan."""
    plan = []

    # Check what sections the reference agents have that this agent doesn't
    ref_sections = defaultdict(list)
    for _wc, _total, ref_id, ref_path in ref_agents:
        content = ref_path.read_text(encoding="utf-8")
        body = get_body(content)
        for section, pattern in CORE_SECTIONS.items():
            import re
            if re.search(pattern, body, re.IGNORECASE):
                ref_sections[section].append(ref_id)

    # Determine which expansion sections to suggest
    agent_content = ""
    try:
        agent_content = Path(analysis["path"]).read_text(encoding="utf-8")
    except Exception:
        pass
    agent_body = get_body(agent_content)

    for section_name, config in EXPANSION_SECTIONS.items():
        # Skip sections the agent already has good coverage of
        if section_name == "Identity & Backstory" and len(agent_body.split()) > 300:
            continue
        if section_name == "Communication Style" and any(
            s for s in ref_sections if "Communication" in s
        ):
            continue
        if section_name == "Success Metrics" and any(
            s for s in ref_sections
            if "Success Metrics" in s and ref_sections.get("Success Metrics")
        ):
            continue

        # For the plan, always suggest improvements unless clearly already A-grade
        if analysis["current_grade"] == "A":
            continue

        if section_name == "Identity & Backstory" and analysis["word_count"] > 400:
            continue

        if section_name == "Critical Rules Enhancement" and analysis["current_scores"].get("structure", 0) >= 3:
            continue

        # Check which reference agents have exemplars for this section
        exemplars = []
        if section_name == "Communication Style":
            exemplars = ref_sections.get("Communication", [])
        elif section_name == "Success Metrics":
            exemplars = ref_sections.get("Success Metrics", [])

        plan.append({
            "section": section_name,
            "priority": config["priority"],
            "target_words": config["target_words"],
            "description": config["description"],
            "template": config["template"],
            "exemplars": exemplars[:3],
        })

    plan.sort(key=lambda x: x["priority"])
    return plan


def print_expansion_plan(analysis, ref_agents, plan):
    """Print a human-readable expansion plan."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Agent Expansion Plan{RESET}")
    print(f"  Agent: {analysis['agent_id']} ({analysis['category']})")
    print(f"  Current: {analysis['current_grade']} ({analysis['current_total']}/10) "
          f"| {analysis['word_count']} words")
    print(f"  Target:  {GREEN}A (8+/10){RESET} | +{analysis['estimated_new_words']} words needed")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Current issues
    if analysis["issues"]:
        print(f"{BOLD}Current Issues:{RESET}")
        for issue in analysis["issues"]:
            print(f"  {RED}✗{RESET} {issue}")
        print()

    # Reference agents
    if ref_agents:
        print(f"{BOLD}Reference A-Grade Agents (same category):{RESET}")
        for _wc, _total, ref_id, _ref_path in ref_agents:
            print(f"  {GREEN}✔{RESET} {ref_id} ({_wc} words, {_total}/10)")
        print()

    # Step-by-step expansion plan
    print(f"{BOLD}Expansion Steps (in order of priority):{RESET}\n")
    total_words = 0
    for i, step in enumerate(plan, 1):
        total_words += step["target_words"]
        print(f"{BOLD}Step {i}: {step['section']}{RESET} "
              f"{YELLOW}(~{step['target_words']} words){RESET}")
        print(f"  {step['description']}")
        if step["exemplars"]:
            print(f"  {CYAN}Reference: {', '.join(step['exemplars'])}{RESET}")
        print()

    print(f"{BOLD}Estimated total: +{total_words} words{RESET}")
    print(f"Projected: {GREEN}{analysis['projected_grade']}{RESET} "
          f"({analysis['word_count'] + total_words} words)\n")

    # Print templates
    print(f"{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  Expansion Templates (copy-paste ready){RESET}")
    print(f"{BOLD}{'─'*60}{RESET}\n")

    for step in plan:
        print(f"{BOLD}── {step['section']} ──{RESET}\n")
        print(step["template"])
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Generate expansion plans for underweight agents")
    parser.add_argument("agent_id", nargs="?",
                        help="Agent ID to generate expansion plan for")
    parser.add_argument("--category", "-c",
                        help="Filter to category")
    parser.add_argument("--all-below", type=int, default=0,
                        help="List all agents below this word count threshold")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview only, don't print templates")
    args = parser.parse_args()

    # --all-below mode: list agents needing expansion
    if args.all_below > 0:
        if not args.category:
            print("ERROR: --all-below requires --category", file=sys.stderr)
            sys.exit(1)

        print(f"\n{BOLD}Agents below {args.all_below} words in '{args.category}':{RESET}\n")
        count = 0
        for _cat, _rel, filepath in discover_agents(category_filter=args.category):
            result = score_agent(filepath, check_freshness=False)
            if result["word_count"] < args.all_below:
                gap = args.all_below - result["word_count"]
                print(f"  {YELLOW}{result['id']}{RESET} — "
                      f"{result['word_count']}w (need +{gap}w)  "
                      f"[{result['grade']} {result['total']}/10]")
                count += 1
        print(f"\n  Total: {count} agents below {args.all_below} words")
        return

    # Single agent mode
    if not args.agent_id:
        parser.print_help()
        sys.exit(1)

    agent_id = args.agent_id

    # Find the agent file
    filepath = None
    category = None
    for _cat, _rel, fp in discover_agents():
        if fp.stem == agent_id:
            filepath = fp
            category = _cat
            break

    if not filepath:
        print(f"ERROR: Agent '{agent_id}' not found.", file=sys.stderr)
        sys.exit(1)

    # Analyze
    analysis = analyze_expansion_needs(agent_id, category, filepath)

    if analysis["current_grade"] == "A":
        print(f"\n{GREEN}Agent '{agent_id}' is already A-grade ({analysis['current_total']}/10).{RESET}")
        print("No expansion needed.")
        return

    # Find reference agents
    ref_agents = find_reference_agents(category, agent_id)

    # Generate plan
    plan = generate_expansion_plan(analysis, ref_agents)

    # Print
    print_expansion_plan(analysis, ref_agents, plan)


if __name__ == "__main__":
    main()
