#!/usr/bin/env python3
"""Batch fix common content quality issues in agent .md files.

Handles:
  4. Placeholder residues ([Domain-specific principle], TODO, etc.)
  5. Duplicate section headings (double ## Deliverables, etc.)
  6. Missing H1 title (starts directly with ## Identity)

Usage:
    python scripts/fix-agent-content.py --dry-run           # report only
    python scripts/fix-agent-content.py                     # apply fixes
    python scripts/fix-agent-content.py --category aerospace
"""

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

from _shared import REPO
from _shared.discovery import discover_agents
from _shared.frontmatter import get_body, get_field, get_frontmatter_text

PLACEHOLDERS = [
    (r"\[Domain-specific principle\]", "domain best practices"),
    (r"\[Proven methodology\]", "proven methodology"),
    (r"\[example[s]?\s*:?\s*.*?\]", ""),
    (r"\[Insert .*?\]", ""),
    (r"\[TODO:?\s*.*?\]", ""),
    (r"\bplaceholder\b", ""),
    (r"\[Add .*? here\]", ""),
    (r"\[Your .*?\]", ""),
    (r"\[To be .*?\]", ""),
]


def has_placeholder(body: str) -> list[str]:
    found = []
    for pattern, _ in PLACEHOLDERS:
        matches = re.findall(pattern, body, re.IGNORECASE)
        found.extend(matches)
    return found


def strip_placeholders(body: str) -> tuple[str, int]:
    count = 0
    for pattern, replacement in PLACEHOLDERS:
        new_body, n = re.subn(pattern, replacement, body, flags=re.IGNORECASE)
        if n:
            count += n
            body = new_body
    return body, count


def find_duplicate_headings(body: str) -> list[str]:
    headings = re.findall(r"^(#{2,4}\s+.+)$", body, re.MULTILINE)
    seen: dict[str, int] = {}
    dupes = []
    for h in headings:
        normalized = h.strip()
        if normalized in seen:
            dupes.append(normalized)
        else:
            seen[normalized] = 1
    return dupes


def deduplicate_headings(body: str) -> tuple[str, int]:
    lines = body.split("\n")
    seen_headings: set[str] = set()
    removed = 0
    result: list[str] = []
    skipping = False
    skip_level = 0
    for line in lines:
        m = re.match(r"^(#{2,4})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            heading_text = f"{'#' * level} {m.group(2)}".strip()
            if heading_text in seen_headings:
                skipping = True
                skip_level = level
                removed += 1
                continue
            if skipping and level <= skip_level:
                skipping = False
            seen_headings.add(heading_text)
        if skipping:
            continue
        result.append(line)
    return "\n".join(result), removed


def has_h1(body: str) -> bool:
    return bool(re.search(r"^#\s+\S", body, re.MULTILINE))


def add_h1(body: str, agent_name: str) -> str:
    title = agent_name.strip()
    return f"# {title}\n\n" + body.lstrip("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix common agent content issues")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--category", help="Filter by category directory")
    args = parser.parse_args()

    agents = list(discover_agents(category_filter=args.category))
    if not agents:
        print("No agents found.", file=sys.stderr)
        sys.exit(1)

    stats = Counter()
    placeholder_agents: list[str] = []
    dupe_heading_agents: list[str] = []
    no_h1_agents: list[str] = []

    for category, rel_path, filepath in agents:
        try:
            content = filepath.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        body = get_body(content)
        fm_text = get_frontmatter_text(content)
        agent_name = get_field("name", fm_text) or filepath.stem

        phs = has_placeholder(body)
        if phs:
            placeholder_agents.append(rel_path)
        dupes = find_duplicate_headings(body)
        if dupes:
            dupe_heading_agents.append(rel_path)
        if not has_h1(body):
            no_h1_agents.append(rel_path)

        if not args.dry_run and (phs or dupes or not has_h1(body)):
            new_body = body
            if phs:
                new_body, n = strip_placeholders(new_body)
                stats["placeholders_fixed"] += n
            if dupes:
                new_body, n = deduplicate_headings(new_body)
                stats["dupes_removed"] += n
            if not has_h1(body):
                new_body = add_h1(new_body, agent_name)
                stats["h1_added"] += 1
            if new_body != body:
                full = "---\n" + fm_text + "---\n" + new_body.lstrip("\n")
                if not full.endswith("\n"):
                    full += "\n"
                filepath.write_text(full, encoding="utf-8", newline="")
                stats["files_fixed"] += 1

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Content Quality Scan ({len(agents)} agents)")
    print(f"  Placeholder residues:  {len(placeholder_agents)} agents")
    print(f"  Duplicate headings:    {len(dupe_heading_agents)} agents")
    print(f"  Missing H1:            {len(no_h1_agents)} agents")

    if args.dry_run:
        if placeholder_agents:
            print(f"\n--- Placeholder agents ({len(placeholder_agents)}) ---")
            for p in placeholder_agents[:15]:
                print(f"  {p}")
            if len(placeholder_agents) > 15:
                print(f"  ... and {len(placeholder_agents) - 15} more")
        if dupe_heading_agents:
            print(f"\n--- Duplicate heading agents ({len(dupe_heading_agents)}) ---")
            for p in dupe_heading_agents[:10]:
                print(f"  {p}")
            if len(dupe_heading_agents) > 10:
                print(f"  ... and {len(dupe_heading_agents) - 10} more")
        if no_h1_agents:
            print(f"\n--- Missing H1 agents ({len(no_h1_agents)}) ---")
            for p in no_h1_agents[:10]:
                print(f"  {p}")
            if len(no_h1_agents) > 10:
                print(f"  ... and {len(no_h1_agents) - 10} more")
        print("\nRun without --dry-run to apply fixes.")
    else:
        print(f"\n  Files fixed:  {stats['files_fixed']}")
        print(f"  Placeholders: {stats['placeholders_fixed']}")
        print(f"  Dupes removed: {stats['dupes_removed']}")
        print(f"  H1 added:     {stats['h1_added']}")


if __name__ == "__main__":
    main()
