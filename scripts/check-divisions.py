#!/usr/bin/env python3
"""Enforce single source of truth for the division set.

divisions.json (repo root) is canonical. This script fails if any of the
following disagree with it:
  1. The actual top-level agent directories on disk
  2. AGENT_DIRS in scripts/convert.sh and scripts/lint-agents.sh
  3. Path filters in .github/workflows/lint-agents.yml
  4. Every divisions.json entry has label, icon, and color
  5. Every division directory contains at least one agent file
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DIVISIONS_JSON = REPO / "divisions.json"

NON_DIVISION_DIRS = {"examples", "scripts", "integrations", "strategy"}


def load_canonical_divisions() -> list[str]:
    with open(DIVISIONS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    return sorted(data["divisions"].keys())


def get_actual_dirs() -> list[str]:
    """Return top-level dirs with git-tracked files, excluding non-division dirs."""
    result = subprocess.run(
        ["git", "-C", str(REPO), "ls-files"],
        capture_output=True, text=True,
    )
    dirs: set[str] = set()
    for line in result.stdout.splitlines():
        parts = line.split("/")
        if len(parts) > 1:
            base = parts[0]
            if base and not base.startswith(".") and base not in NON_DIVISION_DIRS:
                dirs.add(base)
    return sorted(dirs)


def extract_agent_dirs_from_script(script_path: Path) -> list[str]:
    text = script_path.read_text(encoding="utf-8")
    m = re.search(r"AGENT_DIRS=\((.*?)\)", text, re.DOTALL)
    if not m:
        return []
    names = re.findall(r'["\']?([a-z0-9-]+)["\']?', m.group(1))
    return sorted(set(names))


def has_agent_file(directory: Path) -> bool:
    if not directory.is_dir():
        return False
    for f in directory.rglob("*.md"):
        try:
            if f.read_text(encoding="utf-8").startswith("---"):
                return True
        except OSError:
            pass
    return False


def compare_sets(label: str, canonical: list[str], candidate: list[str]) -> list[str]:
    errors: list[str] = []
    canon_set = set(canonical)
    cand_set = set(candidate)
    missing = canon_set - cand_set
    extra = cand_set - canon_set
    if missing:
        errors.append(
            f"ERROR {label} is missing division(s): {', '.join(sorted(missing))}"
        )
    if extra:
        errors.append(
            f"ERROR {label} has extra division(s): {', '.join(sorted(extra))}"
        )
    return errors


def main() -> None:
    if not DIVISIONS_JSON.exists():
        print(f"ERROR {DIVISIONS_JSON} not found")
        sys.exit(1)

    canonical = load_canonical_divisions()
    errors: list[str] = []

    errors += compare_sets(
        "agent directories on disk", canonical, get_actual_dirs()
    )

    for script_name in ["convert.sh", "lint-agents.sh"]:
        script_path = REPO / "scripts" / script_name
        if script_path.exists():
            errors += compare_sets(
                f"scripts/{script_name} AGENT_DIRS",
                canonical,
                extract_agent_dirs_from_script(script_path),
            )

    wf = REPO / ".github" / "workflows" / "lint-agents.yml"
    if wf.exists():
        wf_text = wf.read_text(encoding="utf-8")
        for div in canonical:
            if not re.search(rf"\b{div}/", wf_text):
                errors.append(
                    f"ERROR {wf.relative_to(REPO)} has no path filter for division '{div}'"
                )

    with open(DIVISIONS_JSON, encoding="utf-8") as f:
        data = json.load(f)
    for div in canonical:
        div_data = data["divisions"].get(div, {})
        for field in ("label", "icon", "color"):
            if field not in div_data:
                errors.append(
                    f"ERROR division '{div}' in divisions.json is missing \"{field}\""
                )

    for div in canonical:
        div_dir = REPO / div
        if not div_dir.is_dir():
            errors.append(f"ERROR division '{div}' has no directory on disk")
        elif not has_agent_file(div_dir):
            errors.append(
                f"ERROR division '{div}' has no agent files (.md with '---' frontmatter)"
            )

    if errors:
        for e in errors:
            print(e)
        print("")
        print(f"FAILED: {len(errors)} divisions consistency error(s).")
        sys.exit(1)

    print(f"PASSED: {len(canonical)} divisions consistent across directories, scripts, and CI.")


if __name__ == "__main__":
    main()
