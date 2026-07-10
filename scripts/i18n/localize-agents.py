#!/usr/bin/env python
"""Cross-platform agent localization tool (canonical Python replacement for
localize-agents-zh.ps1).

Reads a translation-mapping JSON file and patches agent .md files by replacing
``name`` and ``description`` fields in the YAML frontmatter with translated
values.

Usage:
    # Patch installed agent directories (default behaviour, matches PS script)
    python scripts/i18n/localize-agents.py

    # Specify custom target directories
    python scripts/i18n/localize-agents.py /path/to/agents ~/custom/agents

    # Localize source agents in the repo
    python scripts/i18n/localize-agents.py --source

    # Preview changes without writing
    python scripts/i18n/localize-agents.py --dry-run

    # Use a different language (loads agent-names-{lang}.json)
    python scripts/i18n/localize-agents.py --lang ja
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _shared import BOLD, GREEN, RED, REPO, RESET, YELLOW  # noqa: E402

I18N_DIR = Path(__file__).resolve().parent
HOME = Path.home()

# Default installed-agent directories (same as PS script defaults)
DEFAULT_INSTALL_DIRS = [
    HOME / ".github" / "agents",
    HOME / ".copilot" / "agents",
]


def ok(msg):    print(f"{GREEN}[OK]{RESET}  {msg}")
def warn(msg):  print(f"{YELLOW}[!!]{RESET}  {msg}")
def info(msg):  print(f"     {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


# ── helpers ─────────────────────────────────────────────────────────────────


def load_map(lang="zh"):
    """Load translation mapping from agent-names-{lang}.json.

    Returns dict of {english_name: {"name": translated_name,
                                    "description": translated_description}}.
    """
    map_path = I18N_DIR / f"agent-names-{lang}.json"
    if not map_path.exists():
        print(f"{RED}Error:{RESET} mapping file not found: {map_path}")
        sys.exit(1)
    with open(map_path, encoding="utf-8") as f:
        return json.load(f)


def get_frontmatter_parts(content):
    """Split content into (before_first_delim, frontmatter, after_second_delim).

    Returns (None, None, None) if content has no valid frontmatter.
    """
    if not content.startswith("---"):
        return None, None, None
    end_idx = content.find("---", 3)
    if end_idx < 0:
        return None, None, None
    # frontmatter is between "---\n" and "\n---"
    fm_text = content[3:end_idx]
    prefix = content[:3]
    suffix = content[end_idx:]
    return prefix, fm_text, suffix


def patch_frontmatter(fm_text, mapping_entry):
    """Replace name and description in frontmatter text.

    Returns (patched_text, changed) where changed is True if any field was
    actually modified.
    """
    changed = False
    lines = fm_text.split("\n")
    new_lines = []
    has_description = False
    for line in lines:
        m_name = re.match(r"^name:\s*(.+)$", line)
        m_desc = re.match(r"^description:\s*(.+)$", line)
        if m_name:
            translated = mapping_entry.get("name", "")
            if translated and m_name.group(1).strip() != translated:
                new_lines.append(f"name: {translated}")
                changed = True
            else:
                new_lines.append(line)
        elif m_desc:
            has_description = True
            translated = mapping_entry.get("description", "")
            if translated and m_desc.group(1).strip() != translated:
                new_lines.append(f"description: {translated}")
                changed = True
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    # If no description field exists but mapping provides one, append it
    if not has_description and mapping_entry.get("description", ""):
        new_lines.append(f"description: {mapping_entry['description']}")
        changed = True

    return "\n".join(new_lines), changed


def process_file(filepath, mapping, dry_run=False):
    """Process a single agent .md file.

    Returns (filepath, action) where action is one of:
      "updated", "skipped" (no mapping), "unchanged" (already patched),
      "no_frontmatter", "error".
    """
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"{RED}Error{RESET} reading {filepath}: {e}")
        return filepath, "error"

    prefix, fm_text, suffix = get_frontmatter_parts(content)
    if prefix is None:
        return filepath, "no_frontmatter"

    # Extract current name to look up translation
    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    if not name_match:
        return filepath, "no_frontmatter"

    current_name = name_match.group(1).strip()
    entry = mapping.get(current_name)
    if not entry:
        return filepath, "skipped"

    new_fm, changed = patch_frontmatter(fm_text, entry)
    if not changed:
        return filepath, "unchanged"

    if not dry_run:
        new_content = prefix + new_fm + suffix
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)

    return filepath, "updated"


def collect_target_files(target_dirs):
    """Collect all .md files from target directories."""
    files = []
    for d in target_dirs:
        d = Path(os.path.expanduser(str(d)))
        if not d.exists():
            print(f"{YELLOW}[!!]{RESET}  Skip (not found): {d}")
            continue
        for md in sorted(d.rglob("*.md")):
            files.append(md)
    return files


def collect_source_agents(repo_root):
    """Collect all agent .md files from the repo source."""
    EXCLUDE_DIRS = {".git", ".github", ".vs", "examples", "integrations",
                    "scripts", "docs", "schemas", "__pycache__"}
    files = []
    for entry in sorted(repo_root.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        for md in sorted(entry.rglob("*.md")):
            files.append(md)
    return files


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Localize agent frontmatter (name + description) from a "
                    "JSON translation mapping.",
    )
    parser.add_argument(
        "target_dirs", nargs="*",
        help="Directories containing installed agent .md files. "
             "Defaults to ~/.github/agents and ~/.copilot/agents.",
    )
    parser.add_argument(
        "--lang", default="zh",
        help="Language code for the mapping file (default: zh, "
             "loads agent-names-zh.json).",
    )
    parser.add_argument(
        "--source", action="store_true",
        help="Process source agents in the repo instead of installed copies.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview changes without writing files.",
    )
    args = parser.parse_args()

    # Determine target directories
    if args.source:
        target_dirs = [REPO]
        header("Localizing source agents in repository")
    elif args.target_dirs:
        target_dirs = args.target_dirs
        header(f"Localizing agents in {len(target_dirs)} target directory(s)")
    else:
        target_dirs = [str(d) for d in DEFAULT_INSTALL_DIRS]
        header("Localizing installed agents")

    print(f"  Language: {args.lang}")
    print(f"  Mapping:  {I18N_DIR / f'agent-names-{args.lang}.json'}")
    if args.dry_run:
        print(f"  Mode:     {YELLOW}dry-run (no files will be modified){RESET}")
    print()

    # Load mapping
    mapping = load_map(args.lang)
    print(f"Loaded {len(mapping)} translation entries.\n")

    # Collect files
    if args.source:
        files = collect_source_agents(REPO)
    else:
        files = collect_target_files(target_dirs)

    if not files:
        print(f"{YELLOW}No agent .md files found in target directories.{RESET}")
        sys.exit(0)

    print(f"Processing {len(files)} agent files...\n")

    # Process files
    stats = {"updated": 0, "skipped": 0, "unchanged": 0,
             "no_frontmatter": 0, "error": 0}
    for f in files:
        rel = str(f)
        try:
            rel = str(f.relative_to(REPO)).replace("\\", "/")
        except ValueError:
            pass

        _path, action = process_file(f, mapping, args.dry_run)
        if action == "updated":
            stats["updated"] += 1
            print(f"{GREEN}  UPD{RESET} {rel}")
        elif action == "unchanged":
            stats["unchanged"] += 1
            print(f"      --- {rel}")
        elif action == "skipped":
            stats["skipped"] += 1
        elif action == "no_frontmatter":
            stats["no_frontmatter"] += 1
        elif action == "error":
            stats["error"] += 1

    # Summary
    print()
    print("=" * 50)
    print(f"  Updated:  {stats['updated']}")
    print(f"  Skipped:  {stats['skipped']} (no translation available)")
    print(f"  Unchanged: {stats['unchanged']} (already localized)")
    if stats["no_frontmatter"]:
        print(f"  No FM:    {stats['no_frontmatter']} (no YAML frontmatter)")
    if stats["error"]:
        print(f"  Errors:   {stats['error']}")
    print("=" * 50)

    if args.dry_run:
        print(f"\n{YELLOW}Dry-run complete. Run without --dry-run to apply changes.{RESET}")
    else:
        print(f"\n{GREEN}Localization complete.{RESET}")


if __name__ == "__main__":
    main()
