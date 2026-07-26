#!/usr/bin/env python
"""Agent feedback collection — the missing feedback loop.

Collects user ratings, comments, and issue reports for installed agents.
Data is stored locally in ``~/.claude/agents/.feedback.jsonl``.

Usage:
    python scripts/feedback.py --agent engineering-frontend-developer --rate 4
    python scripts/feedback.py --agent engineering-frontend-developer --comment "Great React patterns"
    python scripts/feedback.py --agent engineering-frontend-developer --issue "Outdated: suggests CRA"
    python scripts/feedback.py --used engineering-frontend-developer   # record agent usage
    python scripts/feedback.py --prompt                                # prompt to rate recently used agents
    python scripts/feedback.py --report                                # your feedback summary
    python scripts/feedback.py --stats                                 # local feedback statistics
    python scripts/feedback.py --export                                # export feedback as JSON
    python scripts/feedback.py --purge                                 # clear local feedback data
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc

FEEDBACK_FILE = Path.home() / ".claude" / "agents" / ".feedback.jsonl"
USAGE_FILE = Path.home() / ".claude" / "agents" / ".usage.jsonl"


def _ensure_file():
    FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not FEEDBACK_FILE.exists():
        FEEDBACK_FILE.touch()


def _read_all():
    _ensure_file()
    entries = []
    try:
        with open(FEEDBACK_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except (json.JSONDecodeError, OSError):
        pass
    return entries


def _append(entry):
    _ensure_file()
    with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False)
        f.write("\n")


def add_feedback(agent_id, rating=None, comment=None, issue=None):
    entry = {
        "agent": agent_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "hostname": os.environ.get("HOSTNAME", os.environ.get("COMPUTERNAME", "")),
    }
    if rating is not None:
        entry["rating"] = max(1, min(5, int(rating)))
    if comment:
        entry["comment"] = comment[:500]
    if issue:
        entry["issue"] = issue[:500]

    _append(entry)
    return entry


def show_report():
    entries = _read_all()
    if not entries:
        print("No feedback recorded yet.")
        print("  Use: python scripts/feedback.py --agent <id> --rate 1-5")
        return

    by_agent = defaultdict(list)
    for e in entries:
        by_agent[e["agent"]].append(e)

    total = len(entries)
    ratings = [e["rating"] for e in entries if "rating" in e]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    issues = [e for e in entries if "issue" in e]

    print(f"\n{'='*50}")
    print("  Your Agent Feedback")
    print(f"  Total: {total}  |  Avg rating: {avg_rating:.1f}/5  |  Issues: {len(issues)}")
    print(f"{'='*50}\n")

    for agent_id in sorted(by_agent.keys()):
        items = by_agent[agent_id]
        agent_ratings = [e["rating"] for e in items if "rating" in e]
        avg = sum(agent_ratings) / len(agent_ratings) if agent_ratings else float("nan")
        stars = "★" * round(avg) + "☆" * (5 - round(avg)) if agent_ratings else "no rating"

        print(f"  {agent_id}")
        print(f"    {stars} ({len(items)} entries)")
        for e in items:
            ts = e["timestamp"][:19].replace("T", " ")
            if "rating" in e:
                print(f"    [{ts}] rated {e['rating']}/5: {e.get('comment', '')}")
            if "issue" in e:
                print(f"    [{ts}] ISSUE: {e['issue']}")
        print()


def show_stats():
    entries = _read_all()
    if not entries:
        print("No local feedback data available.")
        return

    by_agent = defaultdict(list)
    for e in entries:
        by_agent[e["agent"]].append(e)

    print(f"\n  Feedback entries: {len(entries)}")
    print(f"  Unique agents: {len(by_agent)}")

    agent_scores = []
    for aid, items in by_agent.items():
        ratings = [e["rating"] for e in items if "rating" in e]
        if ratings:
            agent_scores.append((aid, sum(ratings) / len(ratings), len(ratings)))

    if agent_scores:
        agent_scores.sort(key=lambda x: -x[1])
        print("\n  Top rated:")
        for aid, score, count in agent_scores[:10]:
            stars = "★" * round(score) + "☆" * (5 - round(score))
            print(f"    {stars} {aid} ({score:.1f}/5, {count} ratings)")

        agent_scores.sort(key=lambda x: x[1])
        print("\n  Lowest rated:")
        for aid, score, count in agent_scores[:5]:
            stars = "★" * round(score) + "☆" * (5 - round(score))
            print(f"    {stars} {aid} ({score:.1f}/5, {count} ratings)")

    issues = [e for e in entries if "issue" in e]
    if issues:
        print(f"\n  Issues ({len(issues)}):")
        for e in issues[-10:]:
            ts = e["timestamp"][:19].replace("T", " ")
            print(f"    [{ts}] {e['agent']}: {e['issue']}")


def export_feedback():
    entries = _read_all()
    json.dump({"feedback": entries, "count": len(entries),
               "exported": datetime.now(UTC).isoformat()},
              sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def submit_feedback():
    """Generate a GitHub-issue-ready feedback report.

    Outputs a formatted issue body to stdout. Pipe to gh:
        python scripts/feedback.py --submit | gh issue create -t "Feedback Report" -F -
    """
    entries = _read_all()
    if not entries:
        print("No feedback to submit.")
        return

    by_agent = defaultdict(list)
    for e in entries:
        by_agent[e.get("agent", "unknown")].append(e)

    print("## User Feedback Report")
    print(f"Submitted: {datetime.now(UTC).isoformat()[:19]} UTC  ")
    print(f"Entries: {len(entries)} across {len(by_agent)} agents  ")
    print()

    for aid, agent_entries in sorted(by_agent.items()):
        print(f"### {aid} ({len(agent_entries)} entries)")
        for e in agent_entries[-5:]:
            ts = e["timestamp"][:19].replace("T", " ")
            if "rating" in e:
                stars = "★" * e["rating"] + "☆" * (5 - e["rating"])
                print(f"- [{ts}] {stars} ({e['rating']}/5)")
            if e.get("comment"):
                print(f"  - Comment: {e['comment'][:200]}")
            if e.get("issue"):
                print(f"  - Issue: {e['issue'][:200]}")
        print()


def purge_feedback():
    if FEEDBACK_FILE.exists():
        FEEDBACK_FILE.unlink()
        print("Local feedback data cleared.")
    else:
        print("No feedback data to clear.")


def record_usage(agent_id):
    """Record that an agent was used, for proactive rating prompts."""
    USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "agent": agent_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    with open(USAGE_FILE, "a", encoding="utf-8") as f:
        json.dump(entry, f, ensure_ascii=False)
        f.write("\n")
    return entry


def _read_usage():
    """Read usage records, returning {agent_id: use_count}."""
    if not USAGE_FILE.exists():
        return {}
    counts: dict[str, int] = defaultdict(int)
    try:
        with open(USAGE_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        counts[entry.get("agent", "")] += 1
                    except json.JSONDecodeError:
                        continue
    except (json.JSONDecodeError, OSError):
        pass
    return dict(counts)


def prompt_for_feedback():
    """Identify used-but-unrated agents and prompt for feedback."""
    usage = _read_usage()
    feedback_entries = _read_all()
    rated_agents = {e["agent"] for e in feedback_entries if "rating" in e}

    # Find agents used 3+ times but never rated
    unrated = [(aid, count) for aid, count in usage.items()
               if aid not in rated_agents and count >= 3]

    if not unrated:
        print("All frequently used agents have been rated. No prompts needed.")
        # Still show agents with low usage that might need attention
        all_used = sorted(usage.items(), key=lambda x: -x[1])
        if all_used:
            print(f"\nUsage summary ({len(all_used)} agents):")
            for aid, count in all_used[:10]:
                rated = "★" if aid in rated_agents else "○"
                print(f"  {rated} {aid}: used {count} time(s)")
        return

    print(f"\n{len(unrated)} agent(s) used 3+ times but never rated:\n")
    for aid, count in sorted(unrated, key=lambda x: -x[1]):
        print(f"  ○ {aid} — used {count} times")
        print(f"    Rate it: python scripts/feedback.py --agent {aid} --rate 1-5")
        print(f"    Report issue: python scripts/feedback.py --agent {aid} --issue \"...\"")
        print()

    rated_count = len(rated_agents)
    total_used = len(usage)
    print(f"Rated: {rated_count}/{total_used} used agents "
          f"({100 * rated_count / max(total_used, 1):.0f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Agent feedback collection for The Agency")
    parser.add_argument("--agent", "-a", help="Agent ID to provide feedback for")
    parser.add_argument("--rate", type=int, choices=range(1, 6), help="Rating (1-5)")
    parser.add_argument("--comment", "-m", help="Comment about the agent")
    parser.add_argument("--issue", "-i", help="Report an issue with the agent")
    parser.add_argument("--used", help="Record that an agent was used (for usage tracking)")
    parser.add_argument("--prompt", action="store_true",
                        help="Show agents used but not yet rated")
    parser.add_argument("--report", action="store_true", help="Show your feedback summary")
    parser.add_argument("--stats", action="store_true", help="Show local feedback statistics")
    parser.add_argument("--export", action="store_true", help="Export feedback as JSON (stdout)")
    parser.add_argument("--submit", action="store_true", help="Generate GitHub-issue-ready feedback report")
    parser.add_argument("--purge", action="store_true", help="Clear all local feedback data")
    args = parser.parse_args()

    if args.rate or args.comment or args.issue:
        if not args.agent:
            print("ERROR: --agent is required when submitting feedback", file=sys.stderr)
            sys.exit(1)
        entry = add_feedback(args.agent, rating=args.rate,
                             comment=args.comment, issue=args.issue)
        parts = []
        if "rating" in entry:
            parts.append(f"rated {entry['rating']}/5")
        if "comment" in entry:
            parts.append("comment saved")
        if "issue" in entry:
            parts.append("issue recorded")
        print(f"Feedback for '{args.agent}': {', '.join(parts)}")
        return

    if args.used:
        entry = record_usage(args.used)
        print(f"Usage recorded for '{args.used}' at {entry['timestamp'][:19]}")
        return
    if args.prompt:
        prompt_for_feedback()
        return
    if args.report:
        show_report()
        return
    if args.stats:
        show_stats()
        return
    if args.export:
        export_feedback()
        return
    if args.submit:
        submit_feedback()
        return
    if args.purge:
        purge_feedback()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
