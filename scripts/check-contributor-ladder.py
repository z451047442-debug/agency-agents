#!/usr/bin/env python
"""Contributor ladder promotion eligibility checker.

Analyzes git history to identify contributors eligible for promotion
from Contributor → Reviewer → Maintainer based on defined criteria.

Usage:
    python scripts/check-contributor-ladder.py           # full report
    python scripts/check-contributor-ladder.py --json    # machine-readable
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

CRITERIA = {
    "contributor": {"merged_prs": 1},
    "reviewer": {"merged_prs": 3, "reviews": 5},
    "maintainer": {"merged_prs": 10, "reviews": 20},
}


def _run_git(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO), timeout=30)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _count_merged_prs_per_author():
    output = _run_git([
        "git", "log", "main", "--merges", "--format=%an",
        "--since=2025-01-01",
    ])
    counts: dict[str, int] = defaultdict(int)
    for line in output.split("\n"):
        if line.strip():
            counts[line.strip()] += 1
    return dict(counts)


def _count_reviews_per_reviewer():
    output = _run_git([
        "git", "log", "main", "--format=%b",
        "--since=2025-01-01",
    ])
    counts: dict[str, int] = defaultdict(int)
    for line in output.split("\n"):
        if line.startswith("Reviewed-by:") or line.startswith("Co-authored-by:"):
            name = line.split(":", 1)[1].strip().split("<")[0].strip()
            if name and "noreply" not in name.lower():
                counts[name] += 1
    return dict(counts)


def _count_commits_per_author():
    output = _run_git([
        "git", "log", "main", "--no-merges", "--format=%an",
        "--since=2025-01-01",
    ])
    counts: dict[str, int] = defaultdict(int)
    for line in output.split("\n"):
        if line.strip():
            counts[line.strip()] += 1
    return dict(counts)


def check_eligibility():
    prs = _count_merged_prs_per_author()
    reviews = _count_reviews_per_reviewer()
    commits = _count_commits_per_author()

    all_authors = set(list(prs.keys()) + list(reviews.keys()) + list(commits.keys()))

    results = []
    for author in sorted(all_authors):
        author_prs = prs.get(author, 0)
        author_reviews = reviews.get(author, 0)
        author_commits = commits.get(author, 0)

        current = "newcomer"
        if (author_prs >= CRITERIA["maintainer"]["merged_prs"]
                and author_reviews >= CRITERIA["maintainer"]["reviews"]):
            current = "maintainer"
        elif (author_prs >= CRITERIA["reviewer"]["merged_prs"]
                and author_reviews >= CRITERIA["reviewer"]["reviews"]):
            current = "reviewer"
        elif author_prs >= CRITERIA["contributor"]["merged_prs"]:
            current = "contributor"

        results.append({
            "author": author,
            "merged_prs": author_prs,
            "reviews": author_reviews,
            "commits": author_commits,
            "current_level": current,
        })

    return results


def print_report(results, json_output=False):
    if json_output:
        json.dump({
            "criteria": CRITERIA,
            "contributors": results,
        }, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return

    levels: dict[str, list] = defaultdict(list)
    for r in results:
        levels[r["current_level"]].append(r)

    print("\n=== Contributor Ladder Report ===\n")

    for level, label in [("maintainer", "Maintainers"), ("reviewer", "Reviewers"),
                          ("contributor", "Contributors"), ("newcomer", "Newcomers")]:
        members = levels.get(level, [])
        print(f"{label} ({len(members)}):")
        for r in sorted(members, key=lambda x: -x["merged_prs"]):
            next_level = ""
            if level == "newcomer":
                need = max(0, CRITERIA["contributor"]["merged_prs"] - r["merged_prs"])
                next_level = f"  → Contributor (need {need} more PR)"
            elif level == "contributor":
                need_prs = max(0, CRITERIA["reviewer"]["merged_prs"] - r["merged_prs"])
                need_rev = max(0, CRITERIA["reviewer"]["reviews"] - r["reviews"])
                next_level = f"  → Reviewer (need {need_prs} PR + {need_rev} reviews)"
            elif level == "reviewer":
                need_prs = max(0, CRITERIA["maintainer"]["merged_prs"] - r["merged_prs"])
                need_rev = max(0, CRITERIA["maintainer"]["reviews"] - r["reviews"])
                next_level = f"  → Maintainer (need {need_prs} PR + {need_rev} reviews)"
            print(f"  {r['author']:<30s} PRs={r['merged_prs']:>3d}  "
                  f"reviews={r['reviews']:>3d}  commits={r['commits']:>4d}{next_level}")
        print()


def main():
    parser = argparse.ArgumentParser(description="Check contributor ladder eligibility")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = check_eligibility()
    print_report(results, json_output=args.json)


if __name__ == "__main__":
    main()
