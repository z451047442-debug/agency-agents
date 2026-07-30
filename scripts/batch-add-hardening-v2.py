#!/usr/bin/env python3
"""Batch add phase-4-hardening to nexus_roles for agents with hardening keywords (v2).

Uses suggest-nexus-roles keyword analysis to find candidates automatically,
rather than a hardcoded candidate list.

Usage:
    python scripts/batch-add-hardening-v2.py --dry-run           # preview only
    python scripts/batch-add-hardening-v2.py                     # apply
    python scripts/batch-add-hardening-v2.py --category testing  # single category
    python scripts/batch-add-hardening-v2.py --min-confidence 3  # stricter matching
"""

import argparse
import re
import sys
from pathlib import Path

from _shared import GREEN, RED, RESET, YELLOW, atomic_write
from _shared.discovery import EXCLUDE_DIRS, discover_agents

ROOT = Path(__file__).resolve().parent.parent

HARDENING_KEYWORDS = [
    "testing", "qa", "security review", "performance", "optimization",
    "hardening", "code review", "linting", "audit", "quality",
    "vulnerability", "validation", "verification", "benchmark", "refactor",
]


def needs_hardening(body: str, min_confidence: int = 2) -> bool:
    body_lower = body.lower()
    count = 0
    for kw in HARDENING_KEYWORDS:
        if re.search(rf"\b{re.escape(kw)}\b", body_lower):
            count += 1
        if count >= min_confidence:
            return True
    return False


def add_hardening_role(filepath: Path):
    content = filepath.read_text(encoding="utf-8")
    lines = content.splitlines(True)

    # Find frontmatter boundaries
    fm_start = None
    fm_end = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            if fm_start is None:
                fm_start = i
            elif fm_end is None:
                fm_end = i
                break

    if fm_start is None or fm_end is None:
        return False

    # Check if already has phase-4-hardening
    fm_text = "".join(lines[fm_start + 1:fm_end])
    if "phase-4-hardening" in fm_text:
        return False  # already present, idempotent

    # Find insertion point: after nexus_roles list start, or after date_added
    inserted = False
    new_lines = []
    in_nexus_roles = False

    for i, line in enumerate(lines[:fm_end]):
        new_lines.append(line)
        if not inserted:
            if re.match(r"^nexus_roles:", line):
                in_nexus_roles = True
            elif in_nexus_roles and re.match(r"^\s+- ", line):
                pass  # keep scanning nexus_roles items
            elif in_nexus_roles and not re.match(r"^\s+- ", line):
                # End of nexus_roles block — insert before this line
                new_lines.insert(-1, "  - phase-4-hardening\n")
                inserted = True
                in_nexus_roles = False
            elif re.match(r"^date_added:", line) and not in_nexus_roles:
                # No nexus_roles yet — insert it after date_added
                new_lines.append("nexus_roles:\n")
                new_lines.append("  - phase-4-hardening\n")
                inserted = True

    if not inserted:
        # Append to end of frontmatter
        new_lines.insert(-1, "nexus_roles:\n")
        new_lines.insert(-1, "  - phase-4-hardening\n")

    new_lines.extend(lines[fm_end:])
    new_content = "".join(new_lines)
    atomic_write(filepath, new_content, newline="")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Batch add phase-4-hardening to agents matching hardening keywords"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no writes")
    parser.add_argument("--category", "-c", help="Only process one category")
    parser.add_argument("--min-confidence", type=int, default=2,
                        help="Minimum keyword matches (default: 2)")
    args = parser.parse_args()

    candidates = []
    for _cat, _rel, filepath in discover_agents(category_filter=args.category):
        if filepath.name.startswith("."):
            continue
        try:
            body = filepath.read_text(encoding="utf-8")
        except OSError:
            continue
        parts = body.split("---", 2)
        body_text = parts[2] if len(parts) >= 3 else body
        if needs_hardening(body_text, args.min_confidence):
            candidates.append(filepath)

    print(f"Found {len(candidates)} candidates for hardening role")

    if args.dry_run:
        print(f"{YELLOW}DRY RUN — no changes written{RESET}")
        for f in candidates:
            print(f"  {f.relative_to(ROOT)}")
        return

    added = 0
    skipped = 0
    for f in candidates:
        if add_hardening_role(f):
            print(f"  {GREEN}+ hardening{RESET} {f.relative_to(ROOT)}")
            added += 1
        else:
            skipped += 1

    print(f"\nAdded: {added} | Already had: {skipped}")


if __name__ == "__main__":
    main()
