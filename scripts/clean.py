#!/usr/bin/env python3
"""Cleanup generated and temporary files for The Agency."""

import argparse
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

INTEGRATION_TARGETS: list[tuple[str, str | None]] = [
    ("antigravity/agency-*", "dirs"),
    ("gemini-cli/skills", "dir"),
    ("gemini-cli/gemini-extension.json", "file"),
    ("opencode/agents", "dir"),
    ("cursor/rules", "dir"),
    ("aider/CONVENTIONS.md", "file"),
    ("windsurf/.windsurfrules", "file"),
    ("openclaw", "dir_contents_except_readme"),
    ("qwen/agents", "dir"),
    ("kimi", "subdirs"),
]

DEEP_PATTERNS: list[tuple[str, str]] = [
    ("**/__pycache__", "dir"),
    ("**/*.pyc", "file"),
    ("**/.DS_Store", "file"),
    ("**/Thumbs.db", "file"),
    ("**/*.tmp", "file"),
    ("**/*.temp", "file"),
    ("**/.cache", "dir"),
]


def format_bytes(b: int) -> str:
    if b >= 1073741824:
        return f"{b / 1073741824:.1f}GB"
    if b >= 1048576:
        return f"{b / 1048576:.1f}MB"
    if b >= 1024:
        return f"{b / 1024:.1f}KB"
    return f"{b}B"


def count_size(path: Path) -> tuple[int, int]:
    """Return (file_count, total_bytes) for a path."""
    if path.is_file():
        try:
            return 1, path.stat().st_size
        except OSError:
            return 0, 0
    if path.is_dir():
        files = 0
        size = 0
        for f in path.rglob("*"):
            if f.is_file():
                try:
                    size += f.stat().st_size
                    files += 1
                except OSError:
                    pass
        return files, size
    return 0, 0


def collect_integration_paths() -> list[Path]:
    paths: list[Path] = []
    base = REPO / "integrations"

    for target, kind in INTEGRATION_TARGETS:
        if kind == "file":
            p = base / target
            if p.exists():
                paths.append(p)
        elif kind == "dir":
            p = base / target
            if p.is_dir():
                paths.append(p)
        elif kind == "dirs":
            for d in sorted(base.glob(target)):
                if d.is_dir():
                    paths.append(d)
        elif kind == "subdirs":
            for d in sorted(base.glob(f"{target}/*")):
                if d.is_dir():
                    paths.append(d)
        elif kind == "dir_contents_except_readme":
            src = base / target
            if src.is_dir():
                for item in sorted(src.iterdir()):
                    if item.name != "README.md":
                        paths.append(item)

    return paths


def collect_deep_paths() -> list[Path]:
    paths: list[Path] = []
    for pattern, _kind in DEEP_PATTERNS:
        for p in sorted(REPO.glob(pattern)):
            if "env" in p.parts or ".git" in p.parts:
                continue
            paths.append(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cleanup generated and temporary files for The Agency"
    )
    parser.add_argument("--all", dest="deep", action="store_true",
                        help="Deep clean (integrations + temp + pycache)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview what would be deleted")
    args = parser.parse_args()

    paths = collect_integration_paths()
    if args.deep:
        paths += collect_deep_paths()

    if not paths:
        print("Nothing to clean.")
        return

    total_files = 0
    total_bytes = 0
    total_dirs = 0

    for p in paths:
        fc, sz = count_size(p)
        total_files += fc
        total_bytes += sz
        if p.is_dir():
            total_dirs += 1

        if args.dry_run:
            try:
                rel = str(p.relative_to(REPO)).replace("\\", "/")
            except ValueError:
                rel = str(p)
            if p.is_file():
                print(f"  {rel} (1 file, {format_bytes(sz)})")
            else:
                print(f"  {rel}/ ({fc} files, {format_bytes(sz)})")

    pretty = format_bytes(total_bytes)

    if args.dry_run:
        print("")
        print(f"  ... {len(paths)} paths, {total_files} files, {pretty} total")
        print("")
        print("Run without --dry-run to clean.")
        return

    for p in paths:
        if p.is_dir():
            shutil.rmtree(p)
        elif p.is_file():
            p.unlink()

    print(f"Cleaned integrations: {total_dirs} dirs, {total_files} files, {pretty} freed.")
    if args.deep:
        print("Done.")


if __name__ == "__main__":
    main()
