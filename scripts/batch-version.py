#!/usr/bin/env python3
"""Bulk-add version: "1.0.0" to YAML frontmatter of agents that lack it."""

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
VERSION_STRING = 'version: "1.0.0"'

NON_AGENT_DIRS = frozenset({
    ".git", ".github", ".vs", ".vscode", ".claude",
    "examples", "integrations", "scripts", "docs", "schemas", "tests",
    "__pycache__", "env",
})


def is_agent(path: Path) -> bool:
    try:
        return path.read_text(encoding="utf-8").startswith("---")
    except OSError:
        return False


def discover_files(category: str | None = None) -> list[Path]:
    files: list[Path] = []
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name in NON_AGENT_DIRS:
            continue
        if category and entry.name != category:
            continue
        for md in sorted(entry.rglob("*.md")):
            if is_agent(md):
                files.append(md)
    return files


def get_frontmatter(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def has_field(path: Path, field: str) -> bool:
    fm = get_frontmatter(path)
    prefix = f"{field}:"
    for line in fm.split("\n"):
        if line.startswith(prefix):
            return True
    return False


def insert_version(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").split("\n")
    for i, line in enumerate(lines):
        if line.startswith("color:"):
            lines.insert(i + 1, VERSION_STRING)
            break
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Bulk-add version: "1.0.0" to agent YAML frontmatter'
    )
    parser.add_argument("--category", "-c", help="Only process one category")
    parser.add_argument("--file", "-f", help="Process a single agent file")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview without applying")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file).resolve()
        if not path.is_file():
            print(f"ERROR: file not found: {args.file}")
            sys.exit(1)
        files = [path]
    elif args.category:
        cat_dir = REPO / args.category
        if not cat_dir.is_dir():
            print(f"ERROR: category directory not found: {args.category}")
            sys.exit(1)
        files = discover_files(args.category)
    else:
        files = discover_files()

    if not files:
        print("No agent files found.")
        return

    total_checked = 0
    total_has = 0
    total_needs = 0
    total_updated = 0
    total_errors = 0
    samples: list[str] = []
    errors: list[str] = []

    for f in files:
        total_checked += 1
        try:
            rel = str(f.relative_to(REPO)).replace("\\", "/")
        except ValueError:
            rel = str(f)

        if not is_agent(f):
            total_errors += 1
            errors.append(f"{rel}: missing frontmatter")
            continue

        if has_field(f, "version"):
            total_has += 1
            continue

        total_needs += 1

        if not has_field(f, "color"):
            total_errors += 1
            errors.append(f"{rel}: no color: field to anchor version insertion")
            continue

        if len(samples) < 5:
            samples.append(rel)

        if args.dry_run:
            continue

        try:
            insert_version(f)
            total_updated += 1
        except OSError:
            total_errors += 1
            errors.append(f"{rel}: write failed")

    if args.category:
        print(f"  {total_checked} agents in {args.category}/")
    elif args.file:
        print("  1 file specified")
    else:
        print(f"  {total_checked} agents across all categories")

    print(f"  {total_has} already have version")
    print(f"  {total_needs} will be updated with {VERSION_STRING}")
    print("")

    if samples:
        print("  Sample changes:")
        for s in samples:
            print(f"    {s}")
            print(f"    + {VERSION_STRING}")
        print("")

    if errors:
        print("  Errors:")
        for e in errors:
            print(f"    {e}")
        print("")

    if args.dry_run:
        print("Run without --dry-run to apply.")
    elif total_updated > 0:
        print(f"═══ {total_updated} files updated")
    elif total_needs == 0:
        print("═══ All agents already have version fields.")

    if total_errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
