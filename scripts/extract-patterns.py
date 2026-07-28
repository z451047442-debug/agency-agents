#!/usr/bin/env python3
"""Extract improvement patterns from user feedback data.

Analyzes feedback collected by feedback.py to surface actionable insights:
low-rated agents, common issues, and concrete improvement suggestions.
Inspired by ECC's learn / evolve pattern.

Usage:
    python scripts/extract-patterns.py                    # full report
    python scripts/extract-patterns.py --agent <id>       # single agent
    python scripts/extract-patterns.py --json             # machine-readable
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

from _shared import BOLD, GREEN, RED, REPO, RESET, YELLOW

FEEDBACK_FILE = REPO / "feedback.json"


def load_feedback() -> list[dict]:
    if not FEEDBACK_FILE.exists():
        return []
    with open(FEEDBACK_FILE, encoding="utf-8") as f:
        return json.load(f)


def analyze(feedback: list[dict]) -> dict:
    if not feedback:
        return {"total": 0, "by_agent": {}, "issues": [], "top_rated": [], "low_rated": []}

    by_agent: dict[str, list[int]] = defaultdict(list)
    issue_counts: Counter[str] = Counter()

    for entry in feedback:
        aid = entry.get("agent_id", "unknown")
        rating = entry.get("rating")
        issue = entry.get("issue", "")
        if rating is not None:
            by_agent[aid].append(rating)
        if issue:
            issue_counts[issue] += 1

    agent_stats = {}
    for aid, ratings in by_agent.items():
        avg = sum(ratings) / len(ratings)
        agent_stats[aid] = {"avg": round(avg, 1), "count": len(ratings)}

    sorted_agents = sorted(agent_stats.items(), key=lambda x: x[1]["avg"])
    low_rated = [(aid, s) for aid, s in sorted_agents if s["avg"] < 3.0][:10]
    top_rated = [(aid, s) for aid, s in sorted(agent_stats.items(), key=lambda x: -x[1]["avg"])
                 if s["avg"] >= 4.5 and s["count"] >= 2][:10]
    issues = issue_counts.most_common(15)

    return {
        "total": len(feedback),
        "agents_rated": len(agent_stats),
        "by_agent": agent_stats,
        "issues": [(issue, count) for issue, count in issues],
        "top_rated": top_rated,
        "low_rated": low_rated,
    }


def print_report(analysis: dict) -> None:
    if analysis["total"] == 0:
        print("No feedback data yet. Use feedback.py to collect ratings.")
        return

    print(f"{BOLD}=== Feedback Pattern Analysis ==={RESET}\n")
    print(f"Total responses: {analysis['total']}")
    print(f"Agents rated:    {analysis['agents_rated']}")
    print()

    if analysis["low_rated"]:
        print(f"{BOLD}{RED}Needs improvement (avg < 3.0):{RESET}")
        for aid, stats in analysis["low_rated"][:5]:
            print(f"  {RED}{aid}{RESET}: {stats['avg']}/5 ({stats['count']} ratings)")

    if analysis["top_rated"]:
        print(f"\n{BOLD}{GREEN}Top performers (avg >= 4.5):{RESET}")
        for aid, stats in analysis["top_rated"][:5]:
            print(f"  {GREEN}{aid}{RESET}: {stats['avg']}/5 ({stats['count']} ratings)")

    if analysis["issues"]:
        print(f"\n{BOLD}{YELLOW}Common issues:{RESET}")
        for issue, count in analysis["issues"][:8]:
            print(f"  [{count}x] {issue}")

    suggestions = []
    for issue, _ in analysis["issues"]:
        if "outdated" in issue.lower():
            suggestions.append(f"Review agent freshness — {issue}")
        elif "thin" in issue.lower() or "short" in issue.lower():
            suggestions.append(f"Expand agent content — {issue}")
        elif "wrong" in issue.lower() or "incorrect" in issue.lower():
            suggestions.append(f"Verify agent accuracy — {issue}")

    if suggestions:
        print(f"\n{BOLD}Suggested actions:{RESET}")
        for s in suggestions:
            print(f"  {YELLOW}→{RESET} {s}")

    if not analysis["low_rated"] and not analysis["issues"]:
        print(f"{GREEN}All feedback is positive.{RESET}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract improvement patterns from feedback")
    parser.add_argument("--agent", help="Deep-dive on a single agent")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    feedback = load_feedback()
    analysis = analyze(feedback)

    if args.json:
        json.dump(analysis, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    if args.agent:
        stats = analysis["by_agent"].get(args.agent)
        if stats:
            print(f"{BOLD}{args.agent}{RESET}: {stats['avg']}/5 ({stats['count']} ratings)")
        else:
            print(f"No feedback for {args.agent}")
        return

    print_report(analysis)


if __name__ == "__main__":
    main()
