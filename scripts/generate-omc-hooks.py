#!/usr/bin/env python3
"""Generate oh-my-claudecode keyword-detection hooks from agent metadata.

Extracts keywords from agent names and descriptions, groups them into hook
rules, and outputs JSON that can be merged into Claude Code's settings.json.

Usage:
    python scripts/generate-omc-hooks.py                        # all hooks
    python scripts/generate-omc-hooks.py --top 50               # top 50 triggers
    python scripts/generate-omc-hooks.py --category engineering
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any, cast

from _shared import REPO, atomic_write

INDEX_PATH = REPO / "AGENTS.json"
OUT_PATH = REPO / "integrations" / "oh-my-claudecode" / "hooks.json"

STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can",
    "shall", "this", "that", "these", "those", "it", "its",
})

SKIP_TERMS = frozenset({
    "agent", "agents", "expert", "experts", "specialist", "specialists",
    "specialized", "professional", "professionals", "multi", "coordinates",
    "coordinator", "workflows", "coverage", "across", "using", "your",
    "that", "their", "they", "about", "each", "more", "also",
})

PRIORITY_TERMS = {
    "security": 100, "pentest": 100, "vulnerability": 95,
    "architecture": 90, "architect": 90, "kubernetes": 85,
    "database": 80, "compliance": 85, "audit": 80,
    "machine": 80, "learning": 80,
    "devops": 75, "frontend": 70, "backend": 70,
    "mobile": 70, "design": 65, "testing": 65,
    "marketing": 60, "finance": 70, "legal": 75,
    "healthcare": 80, "aerospace": 75, "blockchain": 70,
    "cloud": 75, "network": 70,
    "iot": 65, "robotics": 70,
}


def load_agents() -> list[dict[str, Any]]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f)["agents"])


def extract_keywords(text: str) -> set[str]:
    words = re.findall(r"[a-z]{3,}", text.lower())
    return {w for w in words if w not in STOP_WORDS}


def build_term_map(agents: list[dict]) -> dict[str, list[dict]]:
    term_map: dict[str, list[dict]] = {}
    for a in agents:
        name_kw = extract_keywords(a["name"])
        desc_kw = extract_keywords(a.get("description", ""))
        combined = name_kw | desc_kw

        entry = {"id": a["id"], "name": a["name"], "category": a["category"]}

        for kw in combined:
            if kw not in term_map:
                term_map[kw] = []
            if not any(e["id"] == a["id"] for e in term_map[kw]):
                term_map[kw].append(entry)

    return term_map


def build_triggers(term_map: dict[str, list[dict]], top: int | None) -> list[dict]:
    triggers: list[dict] = []
    for term, agents in term_map.items():
        if len(agents) < 2 or term in SKIP_TERMS:
            continue
        priority = PRIORITY_TERMS.get(term, len(agents) * 2)
        triggers.append({
            "keyword": term,
            "priority": priority,
            "agent_count": len(agents),
            "agents": [a["id"] for a in agents[:10]],
            "categories": sorted({a["category"] for a in agents}),
        })

    triggers.sort(key=lambda t: (-t["priority"], -t["agent_count"]))
    if top:
        triggers = triggers[:top]
    return triggers


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OMC hook triggers from agents")
    parser.add_argument("--top", type=int, help="Limit to top N triggers")
    parser.add_argument("--category", help="Filter by category")
    parser.add_argument("--output", type=Path, default=OUT_PATH,
                        help=f"Output path (default: {OUT_PATH})")
    args = parser.parse_args()

    agents = load_agents()
    if args.category:
        agents = [a for a in agents if a["category"] == args.category]

    print(f"Extracting keywords from {len(agents)} agents...")
    term_map = build_term_map(agents)
    triggers = build_triggers(term_map, args.top)

    print(f"Generated {len(triggers)} hook triggers from {len(term_map)} unique terms")
    print(f"Top triggers: {', '.join(t['keyword'] for t in triggers[:10])}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(args.output,
                 json.dumps({"triggers": triggers}, ensure_ascii=False, indent=2))
    print(f"\nHooks written to: {args.output}")


if __name__ == "__main__":
    main()
