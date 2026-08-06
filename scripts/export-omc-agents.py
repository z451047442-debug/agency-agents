#!/usr/bin/env python3
"""Export agency agents for use with oh-my-claudecode (OMC).

Filters agents by quality score and category, copies them to the Claude Code
agents directory, and generates a filtered index for OMC's explore agent.

Usage:
    python scripts/export-omc-agents.py                           # all agents, score >= 0
    python scripts/export-omc-agents.py --min-score 10            # B-grade and above
    python scripts/export-omc-agents.py --categories engineering,design
    python scripts/export-omc-agents.py --output ~/.claude/agents
    python scripts/export-omc-agents.py --dry-run                  # preview only
    python scripts/export-omc-agents.py --verify                   # check export integrity
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from _shared import REPO, atomic_write

INDEX_PATH = REPO / "AGENTS.json"
SCORE_SCRIPT = REPO / "scripts" / "score-agents.py"
DEFAULT_OUTPUT = Path.home() / ".claude" / "agents"

GRADE_THRESHOLDS = {"A": 12.5, "B": 10.0, "C": 8.0, "D": 0.0}


def grade_label(score: float) -> str:
    for g, t in GRADE_THRESHOLDS.items():
        if score >= t:
            return g
    return "D"


def load_agents() -> list[dict[str, Any]]:
    with open(INDEX_PATH, encoding="utf-8") as f:
        return cast(list[dict[str, Any]], json.load(f)["agents"])


def compute_scores(agents: list[dict]) -> dict[str, float]:
    """Run score-agents.py --json to get scores for all agents."""
    import subprocess

    result = subprocess.run(
        [sys.executable, str(SCORE_SCRIPT), "--json"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    if result.returncode != 0:
        print(f"Warning: scoring failed ({result.stderr.strip()}). All agents get score 0.",
              file=sys.stderr)
        return {a["id"]: 0.0 for a in agents}

    data = json.loads(result.stdout)
    scores: dict[str, float] = {}
    for entry in data.get("agents", []):
        scores[entry["id"]] = entry.get("total", 0.0)
    return scores


def export_agents(
    agents: list[dict],
    scores: dict[str, float],
    output: Path,
    min_score: float,
    categories: set[str] | None,
    dry_run: bool,
) -> tuple[int, list[dict]]:
    """Copy qualifying agents to output directory. Returns (count, exported_list)."""
    output.mkdir(parents=True, exist_ok=True)
    exported: list[dict] = []

    for agent in agents:
        aid = agent["id"]
        score = scores.get(aid, 0.0)
        if score < min_score:
            continue
        if categories and agent["category"] not in categories:
            continue

        source = REPO / agent["path"]
        if not source.exists():
            print(f"  skip: {aid} (source missing: {agent['path']})", file=sys.stderr)
            continue

        dest = output / f"{aid}.md"
        if not dry_run:
            content = source.read_text(encoding="utf-8")
            atomic_write(dest, content)
        exported.append({**agent, "score": round(score, 1), "grade": grade_label(score)})

    if not dry_run and exported:
        write_index(exported, output)

    return len(exported), exported


def write_index(exported: list[dict], output: Path) -> None:
    """Write a filtered AGENTS.json in the output directory."""
    index = {
        "version": "1.0",
        "generated": __import__("datetime").datetime.now().isoformat()[:19],
        "source": "agency-agents → oh-my-claudecode export",
        "total": len(exported),
        "agents": exported,
    }
    atomic_write(output / "AGENTS.json",
                 json.dumps(index, ensure_ascii=False, indent=2))


def verify_export(output: Path) -> bool:
    """Check that all files referenced in AGENTS.json exist and vice versa."""
    index_file = output / "AGENTS.json"
    if not index_file.exists():
        print("FAIL: AGENTS.json not found in output directory")
        return False

    index = json.loads(index_file.read_text(encoding="utf-8"))
    agents = index.get("agents", [])
    errors = 0

    indexed = set()
    for a in agents:
        path = output / f"{a['id']}.md"
        indexed.add(path.name)
        if not path.exists():
            print(f"  missing: {a['id']}.md (in index but not on disk)")
            errors += 1

    on_disk = {p.name for p in output.glob("*.md")}
    for name in sorted(on_disk - indexed - {"README.md"}):
        print(f"  orphan:  {name} (on disk but not in index)")
        errors += 1

    if errors:
        print(f"\nFAIL: {errors} issue(s) found")
        return False
    print(f"OK: {len(agents)} agents verified (index ↔ disk consistent)")
    return True


def show_summary(exported: list[dict], output: Path, dry_run: bool) -> None:
    by_grade: dict[str, int] = {}
    by_cat: dict[str, int] = {}
    for a in exported:
        by_grade[a["grade"]] = by_grade.get(a["grade"], 0) + 1
        by_cat[a["category"]] = by_cat.get(a["category"], 0) + 1

    prefix = "[DRY RUN] " if dry_run else ""
    print(f"\n{prefix}Export summary: {len(exported)} agents → {output}")
    print(f"  Grades: {', '.join(f'{g}:{c}' for g, c in sorted(by_grade.items()))}")
    print(f"  Categories: {len(by_cat)}")
    print(f"  Index: {output / 'AGENTS.json'}")
    if dry_run:
        print("  (no files written — remove --dry-run to export)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Export agency agents for oh-my-claudecode")
    parser.add_argument("--min-score", type=float, default=0.0,
                        help="Minimum quality score (default: 0 = all agents)")
    parser.add_argument("--categories", help="Comma-separated category filter")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help=f"Output directory (default: {DEFAULT_OUTPUT})")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--verify", action="store_true", help="Verify existing export integrity")
    args = parser.parse_args()

    if args.verify:
        ok = verify_export(args.output)
        sys.exit(0 if ok else 1)

    categories = {c.strip() for c in args.categories.split(",")} if args.categories else None

    agents = load_agents()
    print(f"Loaded {len(agents)} agents from AGENTS.json")

    scores = compute_scores(agents)
    scored_count = sum(1 for s in scores.values() if s > 0)
    print(f"Scored {scored_count} agents")

    count, exported_list = export_agents(agents, scores, args.output,
                                         args.min_score, categories, args.dry_run)
    show_summary(exported_list, args.output, args.dry_run)


if __name__ == "__main__":
    main()
