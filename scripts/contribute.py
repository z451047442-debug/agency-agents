#!/usr/bin/env python
"""Community contribution dashboard — shows exactly where and how to help.

Ranks improvement opportunities by (effort × impact), making it easy for
contributors to find meaningful work. Integrates data from score, lint,
lifecycle, and dependency tools.

Usage:
    python scripts/contribute.py                              # full dashboard
    python scripts/contribute.py --skill beginner             # easy fixes first
    python scripts/contribute.py --skill intermediate         # moderate work
    python scripts/contribute.py --skill advanced             # content expansion
    python scripts/contribute.py --category manufacturing     # focus on one area
    python scripts/contribute.py --top 20                     # show top N opportunities
    python scripts/contribute.py --json                       # machine-readable
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
score_agents = SourceFileLoader("score_agents", str(SCRIPT_DIR / "score-agents.py")).load_module()
lint_agents = SourceFileLoader("lint_agents", str(SCRIPT_DIR / "lint-agents.py")).load_module()

REPO = score_agents.REPO

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
CYAN = "\033[0;36m"
MAGENTA = "\033[0;35m"
RESET = "\033[0m"

SKILL_LEVELS = {
    "beginner": {
        "description": "Metadata, frontmatter, and broken link fixes — no domain expertise needed",
        "max_effort": "easy",
        "time_estimate": "5-15 min per agent",
    },
    "intermediate": {
        "description": "Section additions, lint fixes, and moderate content work",
        "max_effort": "moderate",
        "time_estimate": "15-45 min per agent",
    },
    "advanced": {
        "description": "Content expansion, persona creation, and full rewrites",
        "max_effort": "hard",
        "time_estimate": "45 min - 2 hr per agent",
    },
}

IMPACT_WEIGHTS = {
    "content_depth": 3,   # adding words has highest quality impact
    "structure": 2,       # adding sections has moderate impact
    "frontmatter": 1,     # metadata is quick but low impact
    "file_health": 1,     # size/link fixes are quick
    "security": 4,        # security flags need immediate attention
    "lint_errors": 3,     # lint errors are blockers
    "broken_deps": 2,     # broken dependencies
}


def estimate_effort(issues, scores, word_count):
    """Categorize the effort needed to fix an agent."""
    if not issues and all(s >= v for s, v in zip(scores.values(), [2, 3, 2, 2])):
        return "done"

    needs_content = scores.get("content_depth", 0) < 2
    needs_sections = scores.get("structure", 0) < 3
    has_lint_errors = any("ERROR" in str(i) for i in issues)
    has_security = any("SECURITY" in str(i) or "suspicious" in str(i) for i in issues)

    if needs_content or has_lint_errors:
        return "hard"
    elif needs_sections or len(issues) > 2:
        return "moderate"
    elif issues:
        return "easy"
    return "done"


def build_opportunities(category_filter=None):
    """Build the ranked list of contribution opportunities."""
    opportunities = []

    for _cat, _rel, filepath in score_agents.discover_agents(category_filter=category_filter):
        agent_id = filepath.stem
        category = _cat

        # Score
        score_result = score_agents.score_agent(filepath, check_freshness=False)

        # Lint
        lint_errors = []
        lint_warnings = []
        lint_infos = []
        lint_agents.lint_file(filepath, lint_errors, lint_warnings, lint_infos, freshness=False)

        # Security flags
        sec_flags = sum(1 for w in lint_warnings if "SECURITY" in w)
        sec_flags += sum(1 for e in lint_errors if "SECURITY" in e)

        issues = score_result.get("issues", [])
        word_count = score_result.get("word_count", 0)

        effort = estimate_effort(issues, score_result["scores"], word_count)

        if effort == "done":
            continue

        # Calculate impact score
        impact = 0
        scores = score_result["scores"]

        # Content gap impact
        if scores.get("content_depth", 0) < 2:
            gap = max(0, 400 - word_count)
            impact += min(gap / 100, 3) * IMPACT_WEIGHTS["content_depth"]

        # Structure gap impact
        if scores.get("structure", 0) < 3:
            impact += (3 - scores["structure"]) * IMPACT_WEIGHTS["structure"]

        # Frontmatter gap
        if scores.get("frontmatter", 0) < 2:
            impact += (2 - scores["frontmatter"]) * IMPACT_WEIGHTS["frontmatter"]

        # Security flags
        impact += sec_flags * IMPACT_WEIGHTS["security"]

        # Lint errors
        impact += len(lint_errors) * IMPACT_WEIGHTS["lint_errors"]

        # Ease factor: easy=3, moderate=2, hard=1 (higher means more approachable)
        ease = {"easy": 3, "moderate": 2, "hard": 1}.get(effort, 1)

        # Composite score: ease × impact
        priority = ease * impact

        opportunities.append({
            "id": agent_id,
            "category": category,
            "grade": score_result["grade"],
            "total": score_result["total"],
            "word_count": word_count,
            "scores": scores,
            "effort": effort,
            "impact": round(impact, 1),
            "ease": ease,
            "priority": round(priority, 1),
            "issues": issues,
            "security_flags": sec_flags,
            "lint_errors": len(lint_errors),
            "lint_warnings": len(lint_warnings),
            "broken_links": score_result.get("broken_links", 0),
        })

    opportunities.sort(key=lambda x: -x["priority"])
    return opportunities


def print_dashboard(opportunities, args):
    """Print the contribution dashboard."""
    total = len(opportunities)

    # Filter by skill level
    if args.skill:
        max_effort = SKILL_LEVELS[args.skill]["max_effort"]
        opps = [o for o in opportunities
                if {"easy": 0, "moderate": 1, "hard": 2}.get(o["effort"], 3)
                <= {"easy": 0, "moderate": 1, "hard": 2}.get(max_effort, 3)]
    else:
        opps = opportunities

    top_n = args.top or 20
    opps = opps[:top_n]

    # Header
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Community Contribution Dashboard{RESET}")
    print(f"  {date.today()}  |  {total} agents with improvement opportunities")
    if args.skill:
        print(f"  Skill level: {args.skill} — {SKILL_LEVELS[args.skill]['description']}")
        print(f"  Estimated: {SKILL_LEVELS[args.skill]['time_estimate']}")
    if args.category:
        print(f"  Category: {args.category}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Skill level quick stats
    by_effort = defaultdict(int)
    for o in opportunities:
        by_effort[o["effort"]] += 1
    print(f"{BOLD}By Skill Level:{RESET}")
    print(f"  {GREEN}Beginner:{RESET}    {by_effort.get('easy', 0)} opportunities — metadata, links, frontmatter fixes")
    print(f"  {YELLOW}Intermediate:{RESET} {by_effort.get('moderate', 0)} opportunities — section additions, lint cleanup")
    print(f"  {RED}Advanced:{RESET}    {by_effort.get('hard', 0)} opportunities — content expansion, full rewrites")

    # Category summary
    by_cat = defaultdict(list)
    for o in opportunities:
        by_cat[o["category"]].append(o)
    print(f"\n{BOLD}Categories Needing Most Help:{RESET}")
    cat_stats = []
    for cat, cat_opps in by_cat.items():
        avg_priority = sum(o["priority"] for o in cat_opps) / len(cat_opps)
        cat_stats.append((cat, len(cat_opps), avg_priority,
                          sum(1 for o in cat_opps if o["effort"] == "easy"),
                          sum(1 for o in cat_opps if o["effort"] == "moderate"),
                          sum(1 for o in cat_opps if o["effort"] == "hard")))
    cat_stats.sort(key=lambda x: -x[2])
    for cat, count, avg_p, easy, mod, hard in cat_stats[:15]:
        bar = "█" * int(avg_p / max(1, max(s[2] for s in cat_stats)) * 20)
        print(f"  {cat:<28} {avg_p:4.1f} {bar}  ({count:>3}: {GREEN}{easy}e{RESET} {YELLOW}{mod}m{RESET} {RED}{hard}h{RESET})")

    # Top opportunities
    print(f"\n{BOLD}Top {len(opps)} Opportunities (ranked by ease × impact):{RESET}\n")
    print(f"  {'#':<3} {'PRIORITY':<8} {'EFFORT':<12} {'AGENT':<50} {'SCORE':<6} {'WORDS'}")
    print(f"  {'-'*3} {'-'*8} {'-'*12} {'-'*50} {'-'*6} {'-'*6}")

    for i, o in enumerate(opps, 1):
        color = {"easy": GREEN, "moderate": YELLOW, "hard": RED}.get(o["effort"], RESET)
        print(f"  {i:<3} {o['priority']:<8.1f} {color}{o['effort']:<12}{RESET} "
              f"{o['id']:<50} {o['grade']} {o['total']}/10  {o['word_count']}w")

        # Show the first actionable issue
        if o["issues"]:
            print(f"       {YELLOW}→{RESET} {o['issues'][0]}")
        if o["security_flags"] > 0:
            print(f"       {RED}⚠ {o['security_flags']} security flag(s) — needs review{RESET}")

    # Quick start guide
    if not args.skill and not args.category:
        print(f"\n{BOLD}Getting Started:{RESET}")
        print(f"  {GREEN}New contributor?{RESET} Run: python scripts/contribute.py --skill beginner")
        print(f"  {YELLOW}Some experience?{RESET} Run: python scripts/contribute.py --skill intermediate")
        print(f"  {RED}Domain expert?{RESET}   Run: python scripts/contribute.py --skill advanced")
        print(f"  Focus on a category:     --category manufacturing")
        print(f"\n  For each agent, run:     python scripts/expand-agent.py <agent-id>")
        print(f"  To track progress:       python scripts/agent-lifecycle.py --agent <id> --transition review")


def print_json_output(opportunities, args):
    """Machine-readable output."""
    max_effort = None
    if args.skill:
        max_effort = SKILL_LEVELS[args.skill]["max_effort"]

    output = []
    for o in opportunities:
        if max_effort:
            eff_level = {"easy": 0, "moderate": 1, "hard": 2}.get(o["effort"], 3)
            max_level = {"easy": 0, "moderate": 1, "hard": 2}.get(max_effort, 3)
            if eff_level > max_level:
                continue
        output.append(o)

    json.dump({
        "generated": str(date.today()),
        "total_opportunities": len(output),
        "opportunities": output[:args.top] if args.top else output,
    }, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Community contribution dashboard — find where to help")
    parser.add_argument("--skill", choices=["beginner", "intermediate", "advanced"],
                        help="Filter by contributor skill level")
    parser.add_argument("--category", "-c",
                        help="Focus on a specific category")
    parser.add_argument("--top", type=int, default=20,
                        help="Show top N opportunities (default: 20)")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    opportunities = build_opportunities(category_filter=args.category)

    if args.json:
        print_json_output(opportunities, args)
    else:
        print_dashboard(opportunities, args)


if __name__ == "__main__":
    main()
