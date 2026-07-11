#!/usr/bin/env python3
"""Propose nexus_roles for agents based on content keyword analysis.

Scans each agent's body for phase-related keywords and suggests which
NEXUS pipeline phases the agent should participate in.
"""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

PHASE_KEYWORDS: dict[str, list[str]] = {
    "phase-0-discovery": [
        "research", "market analysis", "user research", "discovery",
        "competitive", "audit", "assess", "landscape", "investigate",
        "explore", "survey", "interview", "persona", "journey map", "benchmark",
    ],
    "phase-1-strategy": [
        "strategy", "architecture", "planning", "roadmap", "design system",
        "information architecture", "blueprint", "specification", "scope",
        "requirements", "architecture decision", "system design", "trade-off",
    ],
    "phase-2-foundation": [
        "scaffolding", "setup", "bootstrap", "configuration", "ci/cd",
        "environment", "project init", "repository", "infrastructure",
        "provision", "foundation", "pipeline", "deployment", "monitoring setup",
    ],
    "phase-3-build": [
        "development", "implementation", "coding", "building", "construction",
        "create", "develop", "write code", "deploy", "implement", "build",
        "programming", "engineering", "feature", "component",
    ],
    "phase-4-hardening": [
        "testing", "qa", "security review", "performance", "optimization",
        "hardening", "code review", "linting", "audit", "quality",
        "vulnerability", "validation", "verification", "benchmark", "refactor",
    ],
    "phase-5-launch": [
        "launch", "release", "deployment", "go-live", "production", "rollout",
        "migration", "announcement", "go-to-market", "ship", "publish", "delivery",
    ],
    "phase-6-operate": [
        "monitoring", "maintenance", "support", "operations", "incident",
        "sre", "observability", "iteration", "continuous improvement",
        "feedback", "metrics", "analytics", "reporting",
    ],
}

PHASE_LABELS: dict[str, str] = {
    "phase-0-discovery": "Discovery",
    "phase-1-strategy": "Strategy",
    "phase-2-foundation": "Foundation",
    "phase-3-build": "Build",
    "phase-4-hardening": "Hardening",
    "phase-5-launch": "Launch",
    "phase-6-operate": "Operate",
}

NON_AGENT_DIRS = frozenset({
    ".git", ".github", ".vs", ".vscode", ".claude",
    "examples", "integrations", "scripts", "docs", "schemas", "tests",
    "__pycache__", "env",
})


def is_agent_file(path: Path) -> bool:
    try:
        return path.read_text(encoding="utf-8").startswith("---")
    except OSError:
        return False


def discover_agents(category: str | None = None) -> list[Path]:
    agents: list[Path] = []
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name in NON_AGENT_DIRS:
            continue
        if category and entry.name != category:
            continue
        for md in sorted(entry.rglob("*.md")):
            if is_agent_file(md):
                agents.append(md)
    return agents


def get_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def count_keywords(body_lower: str, keywords: list[str]) -> int:
    count = 0
    for kw in keywords:
        if kw in body_lower:
            count += 1
    return count


def analyze_agent(path: Path, min_confidence: int = 2) -> list[tuple[str, str, int]]:
    body = get_body(path).lower()
    matches: list[tuple[str, str, int]] = []
    for phase_id, keywords in PHASE_KEYWORDS.items():
        count = count_keywords(body, keywords)
        if count >= min_confidence:
            matches.append((phase_id, PHASE_LABELS[phase_id], count))
    return matches


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Suggest nexus_roles for agents based on content analysis"
    )
    parser.add_argument("--category", "-c", help="Only analyze one category")
    parser.add_argument("--file", "-f", help="Analyze a single agent file")
    parser.add_argument(
        "--min-confidence", type=int, default=2,
        help="Minimum keyword matches to suggest a phase (default: 2)",
    )
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"File not found: {args.file}")
            sys.exit(1)
        files = [path]
    elif args.category:
        files = discover_agents(args.category)
    else:
        files = discover_agents()

    analyzed = 0
    suggested = 0

    for f in files:
        if not is_agent_file(f):
            continue

        matches = analyze_agent(f, args.min_confidence)
        analyzed += 1

        if matches:
            suggested += 1
            print(f"── {f.stem} ──")
            for phase_id, label, count in matches:
                print(f"  - {phase_id}  # {label} ({count} keywords)")

    print("")
    print(f"Analyzed: {analyzed} | Suggested: {suggested} | Min confidence: {args.min_confidence}")


if __name__ == "__main__":
    main()
