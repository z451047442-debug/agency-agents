#!/usr/bin/env python
"""Unified quality dashboard for The Agency — combines lint, score, and security.

Produces a per-agent health report showing what each agent needs to improve.
Default output is a summary dashboard; use --agent or --category for detail.

Usage:
    python scripts/quality-report.py                          # full dashboard
    python scripts/quality-report.py --category engineering   # one category
    python scripts/quality-report.py --agent agent-id         # single agent deep dive
    python scripts/quality-report.py --fixable                # agents sorted by ease of improvement
    python scripts/quality-report.py --json                   # machine-readable
"""

import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from _shared import BOLD, CYAN, GREEN, RED, RESET, YELLOW, discover_agents, load_module

_SCRIPTS = Path(__file__).resolve().parent
lint_file = load_module("lint_agents", _SCRIPTS / "lint-agents.py").lint_file
score_agent = load_module("score_agents", _SCRIPTS / "score-agents.py").score_agent

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _estimate_fix_effort(agent_report):
    """Estimate how much effort to bring an agent from current grade to A.

    Returns (effort_level, fix_items) where effort_level is 'easy', 'moderate',
    or 'hard', and fix_items lists specific actions.
    """
    fixes = []
    scores = agent_report.get("scores", {})
    agent_report.get("issues", [])
    lint_errors = agent_report.get("lint_errors", 0)
    lint_warnings = agent_report.get("lint_warnings", 0)
    security_flags = agent_report.get("security_flags", 0)

    # Easy fixes (no content creation needed)
    if scores.get("frontmatter", 0) < 2:
        fixes.append(("easy", "Add missing frontmatter fields (description, vibe, nexus_roles)"))
    if agent_report.get("broken_links", 0) > 0:
        fixes.append(("easy", f"Fix {agent_report['broken_links']} broken internal link(s)"))

    # Moderate fixes (some content work)
    if scores.get("structure", 0) < 3:
        fixes.append(("moderate", "Add missing recommended sections"))
    if scores.get("file_health", 0) < 2:
        fixes.append(("moderate", "Adjust file size into 2-8 KB sweet spot"))
    if lint_warnings > 3:
        fixes.append(("moderate", f"Address {lint_warnings} lint warnings"))

    # Hard fixes (substantial content creation)
    if scores.get("content_depth", 0) < 2:
        fixes.append(("hard", f"Expand content (currently {agent_report.get('word_count', 0)} words, target 400+)"))
    if lint_errors > 0:
        fixes.append(("hard", f"Fix {lint_errors} lint errors"))

    # Security flags require review
    if security_flags > 0:
        fixes.append(("moderate", f"Review {security_flags} security flag(s)"))

    # Determine overall effort
    if not fixes:
        return "done", fixes
    levels = [f[0] for f in fixes]
    if "hard" in levels:
        return "hard", fixes
    elif "moderate" in levels:
        return "moderate", fixes
    else:
        return "easy", fixes


def build_report(category_filter=None, agent_filter=None, check_freshness=True):
    """Build the unified quality report for all (or filtered) agents."""
    agents = {}

    for category, rel, filepath in discover_agents(category_filter=category_filter):
        agent_id = filepath.stem
        if agent_filter and agent_id != agent_filter:
            continue

        # Run scoring
        score_result = score_agent(filepath, check_freshness=check_freshness)

        # Run linting (collect errors/warnings for this file)
        lint_errors = []
        lint_warnings = []
        lint_infos = []
        lint_file(filepath, lint_errors, lint_warnings, lint_infos, freshness=check_freshness)

        # Security-specific findings
        security_count = sum(
            1 for w in lint_warnings if "SECURITY" in w
        ) + sum(1 for e in lint_errors if "SECURITY" in e)

        agents[agent_id] = {
            "id": agent_id,
            "category": category,
            "path": rel,
            "grade": score_result["grade"],
            "total": score_result["total"],
            "scores": score_result["scores"],
            "word_count": score_result.get("word_count", 0),
            "sections_found": score_result.get("sections_found", 0),
            "file_size_kb": score_result.get("file_size_kb", 0),
            "broken_links": score_result.get("broken_links", 0),
            "last_modified": score_result.get("last_modified"),
            "days_since_modified": score_result.get("days_since_modified"),
            "issues": score_result.get("issues", []),
            "lint_errors": len(lint_errors),
            "lint_warnings": len(lint_warnings),
            "security_flags": security_count,
        }

    return agents


def print_dashboard(agents, args):
    """Print the summary dashboard."""
    total = len(agents)
    if total == 0:
        print("No agents found.")
        return

    # Aggregate stats
    grades = defaultdict(int)
    categories = defaultdict(list)
    effort_groups = defaultdict(list)

    for a in agents.values():
        grades[a["grade"]] += 1
        categories[a["category"]].append(a)
        effort, _ = _estimate_fix_effort(a)
        effort_groups[effort].append(a["id"])

    ab_pct = (grades.get("A", 0) + grades.get("B", 0)) / total * 100

    # Header
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  The Agency — Unified Quality Dashboard{RESET}")
    print(f"  Generated: {date.today()}  |  {total} agents")
    if args.category:
        print(f"  Category: {args.category}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Overall health
    print(f"{BOLD}Overall Health{RESET}")
    print(f"  Quality Gate: {GREEN if ab_pct >= 60 else RED}{'PASS' if ab_pct >= 60 else 'FAIL'}{RESET} "
          f"({ab_pct:.0f}% A/B)")
    print(f"  Grade Distribution:  "
          f"{GREEN}A:{grades.get('A', 0)}{RESET}  "
          f"{CYAN}B:{grades.get('B', 0)}{RESET}  "
          f"{YELLOW}C:{grades.get('C', 0)}{RESET}  "
          f"{RED}D:{grades.get('D', 0)}{RESET}")

    # Fixability
    print(f"\n{BOLD}Improvement Landscape{RESET}")
    print(f"  {GREEN}Already A-grade:{RESET} {len(effort_groups.get('done', []))} agents — no action needed")
    print(f"  {CYAN}Easy fixes:{RESET}     {len(effort_groups.get('easy', []))} agents — minor metadata/links fixes")
    print(f"  {YELLOW}Moderate work:{RESET}  {len(effort_groups.get('moderate', []))} agents — sections, file size, lint")
    print(f"  {RED}Heavy work:{RESET}    {len(effort_groups.get('hard', []))} agents — content expansion needed")

    # Category health
    print(f"\n{BOLD}Category Health (sorted by avg score){RESET}")
    cat_stats = []
    for cat, cat_agents in categories.items():
        avg = sum(a["total"] for a in cat_agents) / len(cat_agents)
        a_count = sum(1 for a in cat_agents if a["grade"] == "A")
        d_count = sum(1 for a in cat_agents if a["grade"] == "D")
        issues = sum(len(a["issues"]) for a in cat_agents)
        cat_stats.append((cat, avg, len(cat_agents), a_count, d_count, issues))

    cat_stats.sort(key=lambda x: x[1], reverse=True)
    for cat, avg, count, a_count, d_count, issues in cat_stats:
        bar = "█" * int(avg)
        flag = f" {RED}{issues} issues{RESET}" if issues > count else ""
        print(f"  {cat:<28} {avg:4.1f} {bar}  ({count:>3} agents, {GREEN}{a_count}A{RESET}/{RED}{d_count}D{RESET}){flag}")

    # Top improvement opportunities
    if args.fixable:
        print(f"\n{BOLD}Top Improvement Opportunities (easiest fixes first){RESET}")
        # Sort agents: first by effort level (easy < moderate < hard), then by score gap (lowest first)
        effort_order = {"easy": 0, "moderate": 1, "hard": 2}
        sorted_agents = sorted(
            agents.values(),
            key=lambda a: (effort_order.get(_estimate_fix_effort(a)[0], 3), a["total"])
        )
        for a in sorted_agents[:20]:
            effort, fixes = _estimate_fix_effort(a)
            if effort == "done":
                continue
            color = {"easy": GREEN, "moderate": YELLOW, "hard": RED}.get(effort, RESET)
            print(f"\n  {BOLD}{a['id']}{RESET} ({a['total']}/10 {a['grade']}) — {color}{effort}{RESET}")
            for _level, fix in fixes[:3]:
                print(f"    - {fix}")

    # Security summary
    sec_flagged = [a for a in agents.values() if a["security_flags"] > 0]
    if sec_flagged:
        print(f"\n{BOLD}Security-Flagged Agents ({len(sec_flagged)}){RESET}")
        for a in sec_flagged:
            print(f"  {YELLOW}{a['id']}{RESET} ({a['category']}) — {a['security_flags']} flag(s)")

    # Perimeter warnings
    short = [a for a in agents.values() if a["word_count"] < 100]
    stale = [a for a in agents.values() if (a.get("days_since_modified") or 0) > 365]
    broken = [a for a in agents.values() if a.get("broken_links", 0) > 0]
    print(f"\n{BOLD}Needs Attention:{RESET}")
    print(f"  {RED}{len(short)} short{RESET} (<100 words)  |  "
          f"{YELLOW}{len(stale)} stale{RESET} (>1 year)  |  "
          f"{YELLOW}{len(broken)} broken links{RESET}")


def print_agent_detail(agent):
    """Deep dive on a single agent."""
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  {agent['id']}{RESET}")
    print(f"  Category: {agent['category']}  |  Grade: {agent['grade']} ({agent['total']}/10)")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # Score breakdown
    print(f"{BOLD}Score Breakdown:{RESET}")
    dims = [
        ("Content Depth", "content_depth", 3, f"{agent['word_count']} words"),
        ("Structure", "structure", 3, f"{agent['sections_found']}/7 sections"),
        ("Frontmatter", "frontmatter", 2, "metadata completeness"),
        ("File Health", "file_health", 2, f"{agent['file_size_kb']} KB, {agent.get('broken_links', 0)} broken links"),
    ]
    for label, key, max_score, detail in dims:
        score = agent["scores"].get(key, 0)
        bar = "█" * score + "░" * (max_score - score)
        color = GREEN if score == max_score else YELLOW if score >= max_score / 2 else RED
        print(f"  {label:<16} {color}{bar}{RESET} {score}/{max_score}  ({detail})")

    # Issues
    if agent["issues"]:
        print(f"\n{BOLD}Issues:{RESET}")
        for issue in agent["issues"]:
            print(f"  {RED}✗{RESET} {issue}")

    # Fix recommendations
    effort, fixes = _estimate_fix_effort(agent)
    if effort != "done":
        print(f"\n{BOLD}Recommended Fixes ({effort} effort):{RESET}")
        for level, fix in fixes:
            icon = {"easy": "🟢", "moderate": "🟡", "hard": "🔴"}.get(level, "⚪")
            print(f"  {icon} {fix}")

    # Lint status
    print(f"\n{BOLD}Lint Status:{RESET}")
    if agent["lint_errors"] == 0 and agent["lint_warnings"] == 0:
        print(f"  {GREEN}Clean — no lint issues{RESET}")
    else:
        if agent["lint_errors"]:
            print(f"  {RED}{agent['lint_errors']} error(s){RESET}")
        if agent["lint_warnings"]:
            print(f"  {YELLOW}{agent['lint_warnings']} warning(s){RESET}")

    # Security
    if agent["security_flags"] > 0:
        print(f"  {YELLOW}{agent['security_flags']} security flag(s) — requires human review{RESET}")
    else:
        print(f"  {GREEN}No security flags{RESET}")

    # Freshness
    if agent.get("days_since_modified"):
        days = agent["days_since_modified"]
        label = f"{days} days ago" if days <= 365 else f"{days} days ago (>1 year)"
        color = GREEN if days <= 180 else YELLOW if days <= 365 else RED
        print(f"\n{BOLD}Last Modified:{RESET} {color}{agent['last_modified']} ({label}){RESET}")


def print_json_report(agents):
    """Machine-readable JSON output."""
    output = {
        "generated": str(date.today()),
        "total_agents": len(agents),
        "agents": [],
    }
    for a in agents.values():
        entry = {
            "id": a["id"],
            "category": a["category"],
            "grade": a["grade"],
            "total": a["total"],
            "scores": a["scores"],
            "word_count": a["word_count"],
            "lint_errors": a["lint_errors"],
            "lint_warnings": a["lint_warnings"],
            "security_flags": a["security_flags"],
            "issues": a["issues"],
        }
        effort, fixes = _estimate_fix_effort(a)
        entry["fix_effort"] = effort
        entry["fixes"] = fixes
        output["agents"].append(entry)

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Unified quality dashboard for The Agency agents")
    parser.add_argument("--category", "-c",
                        help="Filter to a specific category")
    parser.add_argument("--agent", "-a",
                        help="Deep dive on a single agent (by ID)")
    parser.add_argument("--fixable", action="store_true",
                        help="Show top improvement opportunities (easiest fixes first)")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    parser.add_argument("--no-freshness", action="store_true",
                        help="Skip git freshness check (faster)")
    args = parser.parse_args()

    agents = build_report(
        category_filter=args.category,
        agent_filter=args.agent,
        check_freshness=not args.no_freshness,
    )

    if args.json:
        print_json_report(agents)
    elif args.agent:
        agent = agents.get(args.agent)
        if agent:
            print_agent_detail(agent)
        else:
            print(f"Agent '{args.agent}' not found.", file=sys.stderr)
            sys.exit(1)
    else:
        print_dashboard(agents, args)


if __name__ == "__main__":
    main()
