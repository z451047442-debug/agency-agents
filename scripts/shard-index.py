#!/usr/bin/env python
"""Shard AGENTS.json into per-category index files for better scalability.

The monolithic AGENTS.json (~470KB for 1183 agents) works today but won't scale
to 5000+ agents. This tool splits it into:

    integrations/by-category/<category>.json   — full agent data per category
    integrations/by-category/_index.json        — category listing with counts

The original AGENTS.json remains the source of truth; these are derived files.

Usage:
    python scripts/shard-index.py                        # shard AGENTS.json
    python scripts/shard-index.py --check                # verify shards are in sync
    python scripts/shard-index.py --stats                # show shard sizes
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INDEX_PATH = REPO / "AGENTS.json"
SHARD_DIR = REPO / "integrations" / "by-category"

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
RED = "\033[0;31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_index():
    if not INDEX_PATH.exists():
        print(f"ERROR: {INDEX_PATH} not found. Run generate-index.sh first.", file=sys.stderr)
        sys.exit(1)
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def shard_index(data):
    """Split agents by category and write per-category JSON files."""
    SHARD_DIR.mkdir(parents=True, exist_ok=True)

    by_category = defaultdict(list)
    for agent in data["agents"]:
        by_category[agent["category"]].append(agent)

    # Write per-category files
    total_bytes = 0
    for cat in sorted(by_category.keys()):
        agents = by_category[cat]
        shard = {
            "category": cat,
            "agent_count": len(agents),
            "generated": data["generated"],
            "agents": agents,
        }
        filepath = SHARD_DIR / f"{cat}.json"
        content = json.dumps(shard, indent=2, ensure_ascii=False)
        filepath.write_text(content, encoding="utf-8")
        total_bytes += len(content.encode("utf-8"))

    # Write category index
    cat_index = {
        "generated": data["generated"],
        "total_agents": data["total_agents"],
        "total_categories": len(by_category),
        "categories": [
            {
                "category": cat,
                "agent_count": len(agents),
                "file": f"{cat}.json",
                "size_kb": round(
                    len(json.dumps({"agents": agents}, indent=2, ensure_ascii=False).encode("utf-8")) / 1024, 1
                ),
            }
            for cat, agents in sorted(by_category.items())
        ],
    }
    idx_path = SHARD_DIR / "_index.json"
    idx_path.write_text(json.dumps(cat_index, indent=2, ensure_ascii=False), encoding="utf-8")

    return by_category, total_bytes, cat_index


def check_shards(data):
    """Verify shards are in sync with AGENTS.json."""
    if not SHARD_DIR.exists():
        print(f"{RED}ERROR: Shard directory does not exist. Run without --check first.{RESET}")
        sys.exit(1)

    issues = []
    by_category = defaultdict(list)
    for agent in data["agents"]:
        by_category[agent["category"]].append(agent)

    # Check each category has a shard
    for cat, agents in sorted(by_category.items()):
        shard_path = SHARD_DIR / f"{cat}.json"
        if not shard_path.exists():
            issues.append(f"Missing shard: {cat}.json ({len(agents)} agents)")
            continue

        try:
            shard = json.loads(shard_path.read_text(encoding="utf-8"))
            shard_count = len(shard.get("agents", []))
            if shard_count != len(agents):
                issues.append(
                    f"Count mismatch in {cat}: "
                    f"AGENTS.json has {len(agents)}, shard has {shard_count}"
                )
        except Exception as e:
            issues.append(f"Invalid JSON in {cat}.json: {e}")

    # Check for stale shards (categories that no longer exist)
    for shard_file in sorted(SHARD_DIR.glob("*.json")):
        if shard_file.name == "_index.json":
            continue
        cat = shard_file.stem
        if cat not in by_category:
            issues.append(f"Stale shard: {shard_file.name} (category no longer exists)")

    if issues:
        print(f"{RED}Shard sync check FAILED — {len(issues)} issue(s):{RESET}")
        for issue in issues:
            print(f"  {RED}✗{RESET} {issue}")
        sys.exit(1)
    else:
        print(f"{GREEN}✓ Shards are in sync with AGENTS.json{RESET}")
        print(f"  {len(by_category)} categories, {data['total_agents']} agents")


def print_stats():
    """Show shard size distribution."""
    if not SHARD_DIR.exists():
        print(f"{RED}No shards found. Run without --stats first.{RESET}")
        sys.exit(1)

    shards = []
    for shard_file in sorted(SHARD_DIR.glob("*.json")):
        if shard_file.name == "_index.json":
            continue
        size_kb = shard_file.stat().st_size / 1024
        data = json.loads(shard_file.read_text(encoding="utf-8"))
        count = len(data.get("agents", []))
        shards.append((shard_file.stem, count, size_kb))

    shards.sort(key=lambda x: -x[2])

    print(f"\n{BOLD}Shard Size Distribution{RESET}\n")
    total_agents = sum(s[1] for s in shards)
    total_size = sum(s[2] for s in shards)
    print(f"  Total: {len(shards)} shards, {total_agents} agents, {total_size:.0f} KB")
    print(f"  Original AGENTS.json: {INDEX_PATH.stat().st_size / 1024:.0f} KB")
    print(f"  Largest shard: {shards[0][0]} ({shards[0][2]:.0f} KB, {shards[0][1]} agents)")
    print(f"\n  {'Category':<28} {'Agents':>6} {'Size':>8} {'Bar'}")
    print(f"  {'-'*28} {'-'*6} {'-'*8} {'-'*20}")

    for cat, count, size in shards:
        bar = "█" * int(size / max(1, shards[0][2]) * 20)
        print(f"  {cat:<28} {count:>6} {size:>7.1f}K {bar}")


def main():
    parser = argparse.ArgumentParser(
        description="Shard AGENTS.json into per-category files")
    parser.add_argument("--check", action="store_true",
                        help="Verify shards are in sync with AGENTS.json")
    parser.add_argument("--stats", action="store_true",
                        help="Show shard size distribution")
    args = parser.parse_args()

    data = load_index()

    if args.check:
        check_shards(data)
    elif args.stats:
        print_stats()
    else:
        by_category, total_bytes, cat_index = shard_index(data)
        print(f"\n{GREEN}✓ Index sharded successfully{RESET}")
        print(f"  Categories: {len(by_category)}")
        print(f"  Total agents: {data['total_agents']}")
        print(f"  Total shard size: {total_bytes / 1024:.0f} KB")
        print(f"  Output directory: {SHARD_DIR}")
        print(f"\n  Per-category files: {SHARD_DIR}/<category>.json")
        print(f"  Category index:     {SHARD_DIR}/_index.json")


if __name__ == "__main__":
    main()
