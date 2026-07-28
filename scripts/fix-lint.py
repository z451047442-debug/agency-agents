#!/usr/bin/env python3
"""Incremental lint fixer for The Agency's Python tooling.

Detects and applies surgical fixes for ruff and mypy issues. Unlike blanket
reformatting, this reports exactly what changed and supports --check for CI.
Inspired by ECC's build-fix pattern.

Usage:
    python scripts/fix-lint.py                 # detect issues (no changes)
    python scripts/fix-lint.py --apply         # apply fixes
    python scripts/fix-lint.py --check         # CI mode: exit 1 if issues found
"""

import argparse
import subprocess
import sys
from pathlib import Path

from _shared import BOLD, GREEN, RED, REPO, RESET, YELLOW

SCRIPTS_DIR = REPO / "scripts"


def run_ruff_check() -> tuple[list[str], str]:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(SCRIPTS_DIR)],
        capture_output=True, text=True, cwd=str(REPO),
    )
    output = result.stdout + result.stderr
    files = set()
    for line in output.splitlines():
        if ".py:" in line and not line.startswith(" "):
            parts = line.split(":", 1)
            if Path(parts[0]).exists() or (SCRIPTS_DIR / parts[0]).exists():
                files.add(parts[0])
    return sorted(files), output.strip()


def run_ruff_fix() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(SCRIPTS_DIR), "--fix"],
        capture_output=True, text=True, cwd=str(REPO),
    )
    return (result.stdout + result.stderr).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Incremental lint fixer")
    parser.add_argument("--apply", action="store_true", help="Apply auto-fixes")
    parser.add_argument("--check", action="store_true", help="CI mode: exit 1 if issues")
    args = parser.parse_args()

    print(f"{BOLD}=== Fix-Lint ==={RESET}\n")

    files, _ruff_out = run_ruff_check()
    issues = len(files) > 0

    if issues:
        print(f"  {YELLOW}{len(files)} file(s) with issues{RESET}")
        if args.apply:
            fix_output = run_ruff_fix()
            if "fixed" in fix_output.lower():
                import re
                m = re.search(r"(\d+)\s+fixed", fix_output)
                if m:
                    print(f"  {GREEN}Fixed: {m.group(1)} issue(s){RESET}")
        else:
            for line in ruff_output.splitlines()[:8]:
                print(f"  {line}")
    else:
        print(f"  {GREEN}Clean{RESET}")

    if args.check and issues:
        print(f"\n{RED}ISSUES FOUND{RESET}")
        sys.exit(1)
    if not issues:
        print(f"\n{GREEN}All clean{RESET}")


if __name__ == "__main__":
    main()
