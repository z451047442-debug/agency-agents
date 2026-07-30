#!/usr/bin/env python3
"""Match NEXUS agents to a project based on natural language description.

Tokenizes a project description into keywords, scores each agent by keyword
match count in body + description, and returns a roster of top 5 agents
per NEXUS phase.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from _shared import BOLD, CYAN, GREEN, RESET, YELLOW
from _shared.discovery import discover_agents
from _shared.frontmatter import get_body, get_field, get_frontmatter_text, get_list_field

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "shall", "can", "need",
    "dare", "ought", "used", "this", "that", "these", "those", "i", "you",
    "he", "she", "it", "we", "they", "me", "him", "her", "us", "them",
    "my", "your", "his", "its", "our", "their", "mine", "yours", "hers",
    "ours", "theirs", "what", "which", "who", "whom", "whose", "when",
    "where", "why", "how", "all", "each", "every", "both", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "because", "about",
    "into", "over", "after", "before", "between", "under", "above",
    "below", "up", "down", "out", "off", "again",
    "further", "then", "once", "here", "there", "now", "during", "through", "against", "without", "within", "along",
    "around", "among", "across", "behind", "beyond", "inside", "outside",
    "onto", "upon", "via",
})

PHASE_LABELS: dict[str, str] = {
    "phase-0-discovery": "Discovery",
    "phase-1-strategy": "Strategy",
    "phase-2-foundation": "Foundation",
    "phase-3-build": "Build",
    "phase-4-hardening": "Hardening",
    "phase-5-launch": "Launch",
    "phase-6-operate": "Operate",
}


def tokenize(text: str) -> list[str]:
    """Tokenize text into meaningful keywords, filtering stopwords and short words."""
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9#+.]{1,}", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) >= 3]


def score_agent(agent_path: Path, keywords: list[str]) -> int:
    """Score a single agent by counting keyword matches in body + description."""
    try:
        text = agent_path.read_text(encoding="utf-8")
    except OSError:
        return 0
    if not text.startswith("---"):
        return 0

    fm_text = get_frontmatter_text(text)
    body = get_body(text)
    description = get_field("description", fm_text)

    search_text = (body + " " + description).lower()

    score = 0
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw)}\b", search_text):
            score += 1
    return score


def build_roster(project_description: str, phase_filter: str | None = None) -> dict[str, list[dict]]:
    """Build a roster of top 5 agents per NEXUS phase matching the project.

    Returns a dict keyed by phase ID, where each value is a list of up to 5
    agent entries sorted by descending score. Each entry has keys:
        agent_id, category, description, score
    """
    keywords = tokenize(project_description)

    if not keywords:
        return {}

    if phase_filter:
        valid_phases = {phase_filter} if phase_filter in PHASE_LABELS else set()
    else:
        valid_phases = set(PHASE_LABELS.keys())

    phase_scores: dict[str, list[tuple[int, str, str, str]]] = {
        pid: [] for pid in valid_phases
    }

    for _category, _rel_path, file_path in discover_agents():
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if not text.startswith("---"):
            continue

        fm_text = get_frontmatter_text(text)
        nexus_roles = get_list_field("nexus_roles", fm_text)

        if not nexus_roles:
            continue

        description = get_field("description", fm_text) or ""
        body = get_body(text)
        search_text = (body + " " + description).lower()

        score = 0
        for kw in keywords:
            if re.search(rf"\b{re.escape(kw)}\b", search_text):
                score += 1

        if score == 0:
            continue

        agent_id = file_path.stem

        for role in nexus_roles:
            if role in valid_phases:
                phase_scores[role].append((score, agent_id, _category, description))

    roster: dict[str, list[dict]] = {}
    for phase_id in sorted(valid_phases):
        entries = phase_scores[phase_id]
        entries.sort(key=lambda x: (-x[0], x[1]))
        roster[phase_id] = [
            {
                "agent_id": agent_id,
                "category": category,
                "description": desc,
                "score": score,
            }
            for score, agent_id, category, desc in entries[:5]
        ]

    return roster


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match NEXUS agents to a project based on natural language description"
    )
    parser.add_argument(
        "--project", "-p", required=True,
        help="Natural language project description",
    )
    parser.add_argument(
        "--phase", "-P",
        help="Filter to a specific NEXUS phase (e.g., phase-4-hardening)",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON for machine consumption",
    )
    args = parser.parse_args()

    roster = build_roster(args.project, args.phase)

    if args.json:
        json.dump(roster, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return

    if not roster or not any(v for v in roster.values()):
        print(f"{YELLOW}No matching agents found for: {args.project}{RESET}")
        return

    print(f"{BOLD}## Project: \"{args.project}\"{RESET}")
    print()

    for phase_id in sorted(PHASE_LABELS.keys()):
        if args.phase and phase_id != args.phase:
            continue
        entries = roster.get(phase_id, [])
        if not entries:
            continue
        label = PHASE_LABELS[phase_id]
        print(f"{CYAN}{BOLD}### {phase_id} ({label}){RESET}")
        for entry in entries:
            desc = entry["description"]
            if len(desc) > 80:
                desc = desc[:80] + "..."
            print(
                f"  - {entry['agent_id']} ({entry['category']}) — "
                f"{desc} — {GREEN}score: {entry['score']}{RESET}"
            )
        print()


if __name__ == "__main__":
    main()
