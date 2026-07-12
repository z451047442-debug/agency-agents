#!/usr/bin/env python
"""Generate AGENTS.json — the master index of all agent definitions.

Usage:
    python scripts/generate-index.py [--check] [--out <path>]

    --check   Exit 1 if on-disk AGENTS.json differs from what would be generated.
    --out     Write to a custom path (default: repo-root/AGENTS.json).
"""

import json
import sys
from datetime import date
from pathlib import Path

from _shared import REPO, discover_agents, get_field, get_list_field

DEFAULT_OUT = REPO / "AGENTS.json"


def build_index():
    """Scan all agent .md files and return the index dict."""
    agents = []
    categories: set[str] = set()

    for category, rel_path, file_path in discover_agents():
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm_text = parts[1]

        name = get_field("name", fm_text)
        if not name:
            continue

        description = get_field("description", fm_text)
        emoji = get_field("emoji", fm_text)

        # Derive id, subcategory from file path
        filename = rel_path.rsplit("/", 1)[-1]
        agent_id = filename.replace(".md", "")

        # subcategory: everything between category/ and the filename
        prefix = category + "/"
        rest = rel_path[len(prefix):]
        subdir = rest.rsplit("/", 1)[0] if "/" in rest else ""

        depends_on = get_list_field("depends_on", fm_text) or None
        nexus_roles = get_list_field("nexus_roles", fm_text) or None

        agent = {
            "id": agent_id,
            "name": name,
            "description": description,
            "emoji": emoji,
            "category": category,
            "subcategory": subdir,
            "path": rel_path,
        }
        if depends_on:
            agent["depends_on"] = depends_on
        if nexus_roles:
            agent["nexus_roles"] = nexus_roles
        agents.append(agent)
        categories.add(category)

    agents.sort(key=lambda a: a["id"])

    return {
        "version": "1.0",
        "generated": date.today().isoformat(),
        "agents": agents,
        "total_categories": len(categories),
        "total_agents": len(agents),
    }


def format_json(data):
    """Format index as JSON matching the shell script convention.

    Each agent is a compact one-line JSON object, so git diff shows clean
    single-line additions/removals per agent.
    """
    lines = [
        '{"version":"' + data["version"] + '",'
        '"generated":"' + data["generated"] + '",'
        '"agents":['
    ]
    agents = data["agents"]
    for i, agent in enumerate(agents):
        entry = json.dumps(agent, ensure_ascii=False, separators=(",", ":"))
        if i < len(agents) - 1:
            entry += ","
        lines.append(entry)
    lines.append(
        '],"total_categories":' + str(data["total_categories"]) + ","
        '"total_agents":' + str(data["total_agents"]) + "}"
    )
    return "\n".join(lines) + "\n"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate AGENTS.json index")
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 if on-disk AGENTS.json differs from generated output")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help=f"Output path (default: {DEFAULT_OUT})")
    args = parser.parse_args()

    index = build_index()

    out_path = Path(args.out)

    if args.check:
        if not out_path.exists():
            print(f"ERROR: {out_path} does not exist. "
                  f"Run scripts/generate-index.py first.")
            sys.exit(1)

        try:
            current_data = json.loads(out_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"ERROR: Failed to parse {out_path}: {e}")
            sys.exit(1)

        # Compare parsed data, not raw text.
        # Exclude "generated" — it changes daily and is not meaningful for staleness.
        current_agents = current_data.get("agents", [])
        current_agents.sort(key=lambda a: a["id"])
        stale = (
            current_agents != index["agents"]
            or current_data.get("total_agents") != index["total_agents"]
            or current_data.get("total_categories") != index["total_categories"]
        )
        if stale:
            print(f"ERROR: AGENTS.json is stale. "
                  f"Run scripts/generate-index.py and commit the result.")
            sys.exit(1)
        print(f"OK: AGENTS.json is up to date "
              f"({index['total_agents']} agents, "
              f"{index['total_categories']} categories).")
        sys.exit(0)

    generated = format_json(index)
    out_path.write_text(generated, encoding="utf-8")
    print(f"Generated {out_path} "
          f"({index['total_agents']} agents, "
          f"{index['total_categories']} categories).")


if __name__ == "__main__":
    main()
