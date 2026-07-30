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

    # --- Pass 1: Scan entire frontmatter for nexus_roles and date_added ---
    nexus_roles_line_idx = None
    nexus_roles_inline = False
    date_added_line_idx = None

    for i in range(fm_start + 1, fm_end):
        stripped = lines[i].rstrip("\n\r")
        if re.match(r"^nexus_roles:", stripped):
            nexus_roles_line_idx = i
            remainder = stripped[len("nexus_roles:"):].strip()
            if remainder.startswith("["):
                nexus_roles_inline = True
            break  # found the first nexus_roles key
        elif re.match(r"^date_added:", stripped):
            date_added_line_idx = i

    # --- Pass 2: Build output lines with insertion ---
    new_lines = []
    i = 0
    inserted = False

    while i < fm_end:
        line = lines[i]

        if not inserted and i == nexus_roles_line_idx:
            if nexus_roles_inline:
                # Inline format: nexus_roles: [phase-0-discovery]
                m = re.match(r"^(nexus_roles:\s*\[)([^\]]*)(\])\s*", line)
                if m:
                    prefix, items_str, suffix = m.group(1), m.group(2), m.group(3)
                    items = [x.strip() for x in items_str.split(",") if x.strip()]
                    if "phase-4-hardening" not in items:
                        items.append("phase-4-hardening")
                    new_lines.append(f"{prefix}{', '.join(items)}{suffix}\n")
                else:
                    new_lines.append(line)
                inserted = True
                i += 1
            else:
                # Block format: write nexus_roles: line, then collect existing items
                new_lines.append(line)
                i += 1
                # Detect indentation of existing items (or default to "  ")
                indent = "  "
                item_re = re.compile(r"^(\s*)- ")
                while i < fm_end and item_re.match(lines[i]):
                    m2 = item_re.match(lines[i])
                    if m2:
                        indent = m2.group(1)
                    new_lines.append(lines[i])
                    i += 1
                # Insert phase-4-hardening at the end of the block using detected indent
                new_lines.append(f"{indent}- phase-4-hardening\n")
                inserted = True
            continue

        if not inserted and nexus_roles_line_idx is None and i == date_added_line_idx:
            # No existing nexus_roles — insert new block after date_added
            new_lines.append(line)
            new_lines.append("nexus_roles:\n")
            new_lines.append("  - phase-4-hardening\n")
            inserted = True
            i += 1
            continue

        new_lines.append(line)
        i += 1

    if not inserted:
        # Fallback: append to end of frontmatter before closing ---
        new_lines.append("nexus_roles:\n")
        new_lines.append("  - phase-4-hardening\n")

    if not inserted:
        # Fallback: append to end of frontmatter before closing ---
        new_lines.append("nexus_roles:\n")
        new_lines.append("  - phase-4-hardening\n")

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
