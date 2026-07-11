#!/usr/bin/env python3
"""Bulk-add date_added frontmatter from git history.

For each agent .md file without a date_added field, looks up the first git
commit that introduced the file and inserts date_added: "YYYY-MM-DD".
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

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


def has_date_added(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    return "date_added:" in content.split("---", 2)[1] if "---" in content else "date_added:" in content


def get_first_commit_date(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(REPO), "log", "--diff-filter=A", "--follow",
         "--format=%ad", "--date=short", "--", str(path)],
        capture_output=True, text=True,
    )
    lines = result.stdout.strip().split("\n")
    return lines[-1] if lines and lines[-1] else None


def insert_date_added(path: Path, date_str: str) -> bool:
    lines = path.read_text(encoding="utf-8").split("\n")
    insert_idx = None
    for i, line in enumerate(lines):
        if line.startswith("version:"):
            insert_idx = i + 1
            break
    if insert_idx is None:
        for i, line in enumerate(lines):
            if line.startswith("color:"):
                insert_idx = i + 1
                break
    if insert_idx is None:
        return False
    lines.insert(insert_idx, f'date_added: "{date_str}"')
    path.write_text("\n".join(lines), encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bulk-add date_added frontmatter from git history"
    )
    parser.add_argument("--category", "-c", help="Only process one category")
    parser.add_argument("--file", "-f", help="Process a single agent file")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.is_file():
            print(f"ERROR: file not found: {args.file}")
            sys.exit(1)
        files = [path]
    else:
        files = discover_files(args.category)

    count = 0
    skipped = 0

    for f in files:
        if has_date_added(f):
            skipped += 1
            continue

        date_str = get_first_commit_date(f)
        if not date_str:
            skipped += 1
            continue

        if args.dry_run:
            print(f'[DRY-RUN] {f.relative_to(REPO)} -> date_added: "{date_str}"')
        else:
            if insert_date_added(f, date_str):
                print(f'{f.relative_to(REPO)} -> date_added: "{date_str}"')
        count += 1

    print("")
    print(f"Updated: {count} | Skipped: {skipped} | Total: {len(files)}")
    if args.dry_run:
        print("(dry-run — no files were changed)")


if __name__ == "__main__":
    main()
