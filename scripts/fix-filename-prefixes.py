#!/usr/bin/env python3
"""Batch-rename agent files with missing category prefixes.

Fixes lint warnings for:
  - finance/securities-*.md → finance/finance-securities-*.md
  - infrastructure/network-engineering-*.md → infrastructure/infrastructure-network-engineering-*.md

Also updates AGENTS.json paths/IDs and depends_on references.

Usage:
    python scripts/fix-filename-prefixes.py --dry-run     # preview
    python scripts/fix-filename-prefixes.py               # execute renames
"""

import argparse
import json
from pathlib import Path

from _shared import REPO, atomic_write

INDEX_PATH = REPO / "AGENTS.json"


def load_index():
    with open(INDEX_PATH, encoding="utf-8") as f:
        return json.load(f)


def save_index(data):
    atomic_write(INDEX_PATH, json.dumps(data, ensure_ascii=False, indent=2))


def plan_renames(agents):
    renames = []
    for agent in agents:
        path = Path(agent["path"])
        old_name = path.stem
        category = path.parent.name
        new_name = None

        if category == "finance" and old_name.startswith("securities-"):
            new_name = f"finance-{old_name}"
        elif category == "infrastructure" and old_name.startswith("network-engineering-"):
            new_name = f"infrastructure-{old_name}"

        if new_name:
            new_id = new_name.replace("_", "-")
            new_rel = f"{category}/{new_name}.md"
            renames.append({
                "old_path": REPO / path,
                "new_path": REPO / category / f"{new_name}.md",
                "old_id": agent["id"],
                "new_id": new_id,
                "old_rel": agent["path"],
                "new_rel": new_rel,
            })
    return renames


def execute_renames(renames, dry_run):
    id_map = {r["old_id"]: r["new_id"] for r in renames}
    path_map = {r["old_id"]: r["new_rel"] for r in renames}

    for r in renames:
        if dry_run:
            continue
        r["old_path"].rename(r["new_path"])
        print(f"  mv {r['old_rel']} -> {r['new_rel']}")

    if dry_run:
        return

    index = load_index()
    for agent in index["agents"]:
        old_id = agent["id"]
        if old_id in id_map:
            agent["id"] = id_map[old_id]
            agent["path"] = path_map[old_id]
        deps = agent.get("depends_on", [])
        if deps:
            new_deps = [id_map.get(d, d) for d in deps]
            if new_deps != deps:
                agent["depends_on"] = new_deps

    save_index(index)
    print(f"\n  Updated AGENTS.json: {len(renames)} IDs, paths, and depends_on refs fixed")


def main():
    parser = argparse.ArgumentParser(description="Fix filename prefix mismatches")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    index = load_index()
    renames = plan_renames(index["agents"])
    print(f"Files to rename: {len(renames)}")
    execute_renames(renames, args.dry_run)
    if args.dry_run:
        print("\n  (no changes made — remove --dry-run to apply)")


if __name__ == "__main__":
    main()
