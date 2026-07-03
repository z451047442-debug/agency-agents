#!/usr/bin/env python
"""Cross-platform Python replacement for scripts/lint-agents.sh.

Validates agent .md files against The Agency's quality standards.

Usage:
    python scripts/lint-agents.py [file ...]
    python scripts/lint-agents.py --all
"""

import os, re, sys
from datetime import date, timedelta
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".git", ".github", ".vs", "examples", "integrations",
                "scripts", "docs", "schemas", "__pycache__"}

REQUIRED_FIELDS = ("name", "description", "emoji", "color")
SECTION_PATTERNS = {
    "Identity": r"identity",
    "Core Mission": r"core\s*mission|mission\s*[—\-]{1,2}",
    "Critical Rules": r"critical\s*rules?|rules?\s*[—\-]{1,2}|rules?\s*you\s*must\s*follow",
    "Deliverable": r"deliverable",
    "Workflow": r"workflow|process|your\s*workflow",
    "Success Metrics": r"success\s*metrics|metrics\s*[—\-]{1,2}",
}
VALID_NEXUS_PHASES = {
    "phase-0-discovery", "phase-1-strategy", "phase-2-foundation",
    "phase-3-build", "phase-4-hardening", "phase-5-launch", "phase-6-operate",
}
SOUL_KEYWORDS = re.compile(
    r"identity|learning.*memory|communication|style|critical[_\s]rule|rules?\s*you\s*must\s*follow",
    re.IGNORECASE,
)


def get_frontmatter_text(content):
    parts = content.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def get_body(content):
    parts = content.split("---", 2)
    return parts[2] if len(parts) >= 3 else ""


def get_field(field, fm_text):
    m = re.search(rf"^{re.escape(field)}:\s*(.+)$", fm_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def get_list_field(field, fm_text):
    """Extract YAML list items under a field (e.g., nexus_roles, depends_on)."""
    items = []
    in_block = False
    for line in fm_text.split("\n"):
        if re.match(rf"^{re.escape(field)}:", line):
            in_block = True
            continue
        if in_block:
            m = re.match(r"^\s+-\s+(.+)$", line)
            if m:
                items.append(m.group(1).strip().strip('"').strip("'"))
            elif re.match(r"^\S", line):
                break
    return items


def discover_agents():
    """Yield (category, file_path) for every agent .md file."""
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        for md in sorted(entry.rglob("*.md")):
            yield entry.name, md


def lint_file(filepath, errors, warnings, infos, freshness=False):
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name  # file is outside repo (e.g., pre-commit temp dir)

    if not filepath.is_file():
        errors.append(f"ERROR {rel}: not a file")
        return

    content = filepath.read_text(encoding="utf-8")

    # 0. CRLF check
    if "\r" in content:
        errors.append(f"ERROR {rel}: CRLF line endings — convert to LF")
        return

    # 1. Frontmatter delimiters
    if not content.startswith("---"):
        errors.append(f"ERROR {rel}: missing frontmatter ---")
        return

    fm_text = get_frontmatter_text(content)
    if not fm_text.strip():
        errors.append(f"ERROR {rel}: empty frontmatter")
        return

    # 2a. YAML parse check
    try:
        yaml.safe_load(fm_text)
    except yaml.YAMLError as e:
        errors.append(f"ERROR {rel}: invalid YAML — {e}")

    # 2b. Required frontmatter fields
    for field in REQUIRED_FIELDS:
        if get_field(field, fm_text) == "":
            errors.append(f"ERROR {rel}: missing frontmatter '{field}'")

    body = get_body(content)

    # 3. Recommended sections
    for section, pattern in SECTION_PATTERNS.items():
        if not re.search(pattern, body, re.IGNORECASE):
            warnings.append(f"WARN  {rel}: missing section '{section}'")

    # 4. Word count
    word_count = len(body.split())
    if word_count < 100:
        warnings.append(f"WARN  {rel}: content too short (< 100 words, got {word_count})")

    # 5. nexus_roles validation
    nexus_roles = get_list_field("nexus_roles", fm_text)
    for role in nexus_roles:
        if role not in VALID_NEXUS_PHASES:
            warnings.append(
                f"WARN  {rel}: unknown nexus_roles value '{role}'. "
                f"Valid: {', '.join(sorted(VALID_NEXUS_PHASES))}"
            )

    # 6. depends_on empty check
    depends_on = get_list_field("depends_on", fm_text)
    dep_raw = get_field("depends_on", fm_text)
    if (depends_on or dep_raw) and not depends_on:
        infos.append(f"INFO  {rel}: depends_on is present but empty")

    # 7. SOUL/AGENTS header coverage
    soul_count = 0
    agents_count = 0
    for line in body.split("\n"):
        if re.match(r"^##\s", line):
            if SOUL_KEYWORDS.search(line):
                soul_count += 1
            else:
                agents_count += 1
    if soul_count == 0:
        warnings.append(f"WARN  {rel}: no SOUL.md-mapped section headers")
    if agents_count == 0:
        warnings.append(f"WARN  {rel}: no AGENTS.md-mapped section headers")

    # 8. Filename prefix consistency
    category = filepath.parent.name
    filename = filepath.stem
    if not filename.startswith(f"{category}-"):
        warnings.append(
            f"WARN  {rel}: filename '{filename}' should start with '{category}-'"
        )

    # 9. Broken internal links
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")
    file_dir = filepath.parent
    for m in link_pattern.finditer(body):
        url = m.group(2)
        if url.startswith("http://") or url.startswith("https://"):
            continue
        if url.startswith("/"):
            target = REPO / url.lstrip("/")
        else:
            target = (file_dir / url).resolve()
        if not target.exists():
            warnings.append(f"WARN  {rel}: broken link '{url}' → target not found")

    # 10. Content freshness (> 12 months stale) — optional, uses git
    if freshness:
        cutoff = date.today() - timedelta(days=365)
        import subprocess
        try:
            result = subprocess.run(
                ["git", "-C", str(REPO), "log", "-1", "--format=%ad", "--date=short", "--", str(filepath)],
                capture_output=True, text=True, timeout=5,
            )
            last_date_str = result.stdout.strip()
            if last_date_str:
                last_date = date.fromisoformat(last_date_str)
                if last_date < cutoff:
                    infos.append(f"INFO  {rel}: last modified {last_date_str} (>12 months ago, may be stale)")
        except Exception:
            pass


def collect_files(paths, all_mode):
    files = []
    if paths:
        for p in paths:
            path = Path(p)
            if path.is_absolute():
                files.append(path)
            else:
                files.append(REPO / path)
    elif all_mode:
        for category, filepath in discover_agents():
            files.append(filepath)
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Lint The Agency agent .md files")
    parser.add_argument("files", nargs="*", help="Agent file(s) to lint")
    parser.add_argument("--all", action="store_true", help="Lint all agents")
    parser.add_argument("--check", action="store_true", help="Alias for --all")
    parser.add_argument("--freshness", action="store_true", help="Check git last-modified date (slow on many files)")
    args = parser.parse_args()

    if not args.files and not args.all and not args.check:
        parser.print_help()
        print("\nUsage: lint-agents.py [file ...] | --all")
        sys.exit(1)

    files = collect_files(args.files, args.all or args.check)

    if not files:
        print("No agent files found.")
        sys.exit(1)

    errors = []
    warnings = []
    infos = []

    print(f"Linting {len(files)} agent files...\n")

    for f in sorted(files):
        lint_file(f, errors, warnings, infos, freshness=args.freshness)

    # Print results
    for e in errors:
        print(e)
    for w in warnings:
        print(w)
    for i in infos:
        print(i)

    print()
    print("═" * 40)
    print(f"Files:    {len(files)}")
    print(f"Errors:   {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Short:    {sum(1 for w in warnings if 'too short' in w)} (< 100 words)")
    print("═" * 40)

    if errors:
        print("FAILED — fix errors before merging")
        sys.exit(1)
    else:
        print("PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
