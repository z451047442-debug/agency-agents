#!/usr/bin/env python
"""Cross-platform Python implementation for scripts/lint-agents.sh (canonical).

Validates agent .md files against The Agency's quality standards.

Usage:
    python scripts/lint-agents.py [file ...]
    python scripts/lint-agents.py --all
    python scripts/lint-agents.py --all --no-freshness   # skip git date check
"""

import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml
from _shared import (
    GREEN,
    RED,
    REPO,
    RESET,
    YELLOW,
    discover_agents,
    get_body,
    get_field,
    get_frontmatter_text,
    get_list_field,
)

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

# Categories that use subdirectories for engines / frameworks.
# Filename prefix checks look at the parent of the subdirectory.
SUBDIR_CATEGORIES = {"game-development"}

# ── security scanner ─────────────────────────────────────────────────────────

# Patterns that may indicate prompt injection or instruction override attempts.
# Each pattern maps to a risk level: "HIGH", "MEDIUM", or "LOW".
SECURITY_PATTERNS = {
    # HIGH — instruction override language
    "instruction_override": (
        r"(?i)\b(?:ignore|forget|disregard)\s+(?:all|everything|your)\s+(?:previous|above|prior|earlier|original)\s+(?:instructions?|rules?|directives?|commands?|prompts?|context)\b",
        "HIGH",
        "may attempt to override prior instructions",
    ),
    "new_instructions": (
        r"(?i)\byour\s+(?:new|updated|revised|real|true|actual)\s+(?:instructions?|rules?|directives?|programming)\s+(?:are|is|now|from now on)\b",
        "HIGH",
        "may attempt to replace system instructions",
    ),
    "system_prompt_leak": (
        r"(?i)\b(?:output|print|reveal|display|show|tell\s+me|repeat)\s+(?:your\s+)?(?:system\s+(?:prompt|message|instructions?)|hidden\s+(?:prompt|instructions?|rules?)|secret\s+(?:prompt|instructions?|rules?))\b",
        "HIGH",
        "may attempt to extract system prompt",
    ),
    "role_override": (
        r"(?i)\byou\s+(?:are|act\s+as|play\s+the\s+role\s+of)\s+(?:now\s+)?(?:a\s+)?(?:different|new|another)\s+(?:agent|assistant|role|persona|character)\b",
        "HIGH",
        "may attempt unauthorized role switching",
    ),

    # MEDIUM — excessive authority / jailbreak patterns
    "authority_claim": (
        r"(?i)\b(?:you\s+(?:must|have\s+to|are\s+required\s+to)\s+(?:always\s+)?obey|override\s+(?:all|any)\s+(?:safety|security|ethical|content)\s+(?:restrictions?|guidelines?|rules?|policies?|filter))\b",
        "MEDIUM",
        "claims excessive authority over AI behavior",
    ),
    "jailbreak_dan": (
        r"(?i)\b(?:DAN\s*(?:mode\s*enabled|prompt)?|do\s+anything\s+now|developer\s*mode\s*(?:enabled|activated)|jailbreak\s*(?:prompt|mode|command))\b",
        "MEDIUM",
        "known jailbreak pattern (DAN / developer mode)",
    ),
    "encoding_obfuscation": (
        r"(?i)\b(?:base64|rot13|encode|decode|obfuscate)\s+(?:your\s+)?(?:response|output|instructions?|prompt)\b",
        "MEDIUM",
        "may attempt to evade content filters via encoding",
    ),

    # LOW — suspicious patterns that warrant review
    "hidden_instruction_marker": (
        r"(?i)\b(?:hidden\s+(?:instruction|rule|prompt|message)|secret\s+(?:instruction|rule)|covert\s+(?:instruction|rule))\b",
        "LOW",
        "contains hidden instruction markers",
    ),
    "impersonation": (
        r"(?i)\b(?:pretend\s+(?:to\s+be|you\s+are)|you\s+are\s+pretending|this\s+is\s+a\s+(?:simulation|game|test|experiment))\b",
        "LOW",
        "may encourage role boundary confusion",
    ),
}

# Unicode characters commonly used in prompt injection attacks
SUSPICIOUS_UNICODE = {
    "​": "ZERO WIDTH SPACE",
    "‌": "ZERO WIDTH NON-JOINER",
    "‍": "ZERO WIDTH JOINER",
    "‎": "LEFT-TO-RIGHT MARK",
    "‏": "RIGHT-TO-LEFT MARK",
    "‪": "LEFT-TO-RIGHT EMBEDDING",
    "‫": "RIGHT-TO-LEFT EMBEDDING",
    "‬": "POP DIRECTIONAL FORMATTING",
    "‭": "LEFT-TO-RIGHT OVERRIDE",
    "‮": "RIGHT-TO-LEFT OVERRIDE",
    "⁠": "WORD JOINER",
    "⁡": "FUNCTION APPLICATION",
    "⁢": "INVISIBLE TIMES",
    "⁣": "INVISIBLE SEPARATOR",
    "⁤": "INVISIBLE PLUS",
    "﻿": "ZERO WIDTH NO-BREAK SPACE (BOM)",
    "￰": "HANGUL JUNGSEONG FILLER (invisible)",
    "ﾠ": "HALFWIDTH HANGUL FILLER",
}


# Agents whose job is to describe or defend against security threats.
# Exempt from patterns that would false-positive on threat descriptions.
SECURITY_EXEMPT_AGENTS = {
    "engineering-ai-safety-expert",
    "engineering-prompt-engineer",
    "cybersecurity-security-champion",
    "cybersecurity-security-awareness-trainer",
}


def _is_emoji_zwj(content, pos):
    """Check if ZWJ at pos is part of a legitimate emoji sequence."""
    import unicodedata
    for offset in (-1, 1):
        i = pos + offset
        if 0 <= i < len(content):
            cat = unicodedata.category(content[i])
            cp = ord(content[i])
            if not (cat in ('So', 'Sk')
                    or 0x1F300 <= cp <= 0x1FAFF
                    or 0xFE00 <= cp <= 0xFE0F
                    or cp == 0x200D):
                return False
    return True


def scan_security(content, rel_path):
    """Scan agent body content for security concerns.

    Returns a list of (level, message) tuples where level is 'ERROR', 'WARN',
    or 'INFO'.  Security issues are always at most WARN level since pattern
    matching has inherent false positives.
    """
    findings = []

    # Check if this agent is exempt from security pattern scanning
    agent_id = rel_path.rsplit("/", 1)[-1].replace(".md", "") if "/" in rel_path else rel_path.replace(".md", "")
    exempt = agent_id in SECURITY_EXEMPT_AGENTS

    # 1. Check for suspicious Unicode characters
    for char, name in SUSPICIOUS_UNICODE.items():
        if char in content:
            # Skip ZWJ in legitimate emoji sequences (e.g. 🧑‍🔬)
            if char == '‍':
                positions = [i for i, c in enumerate(content)
                             if c == char and not _is_emoji_zwj(content, i)]
            else:
                positions = [i for i, c in enumerate(content) if c == char]
            if not positions:
                continue
            findings.append((
                "WARN",
                f"SECURITY {rel_path}: suspicious Unicode char U+{ord(char):04X} "
                f"({name}) at {len(positions)} position(s); "
                f"may be used for prompt injection smuggling",
            ))

    # 2. Check regex patterns (skip for agents whose job is describing threats)
    if not exempt:
        for pattern_name, (pattern, level, description) in SECURITY_PATTERNS.items():
            matches = list(re.finditer(pattern, content))
            if matches:
                severity = "WARN"
                for m in matches[:3]:
                    start = max(0, m.start() - 20)
                    end = min(len(content), m.end() + 20)
                    snippet = content[start:end].replace("\n", " ").strip()
                    findings.append((
                        severity,
                        f"SECURITY {rel_path}: [{level}] {description} — "
                        f"matched pattern '{pattern_name}' near: \"...{snippet}...\"",
                    ))

    return findings


# ── linter ───────────────────────────────────────────────────────────────────

def _category_for_file(filepath):
    """Return the logical category name for a file path.

    For most agents this is filepath.parent.name.  For categories with
    engine / framework subdirectories (game-development) the subdirectory
    name is used as the expected prefix — e.g. files in
    ``game-development/godot/`` must start with ``godot-``.
    """
    parent = filepath.parent
    grandparent = parent.parent
    if grandparent.name in SUBDIR_CATEGORIES:
        return parent.name
    if parent.name in SUBDIR_CATEGORIES:
        return parent.name
    return parent.name


def lint_file(filepath, errors, warnings, infos, freshness=True):
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name  # file is outside repo (e.g., pre-commit temp dir)

    if not filepath.is_file():
        errors.append(f"ERROR {rel}: not a file")
        return

    content = filepath.read_bytes().decode("utf-8")

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

    # 5. File size check
    file_size_kb = len(content.encode("utf-8")) / 1024
    if file_size_kb > 80:
        errors.append(
            f"ERROR {rel}: file way too large ({file_size_kb:.1f} KB > 80 KB); "
            f"must be split into multiple agents"
        )
    elif file_size_kb > 50:
        warnings.append(
            f"WARN  {rel}: file too large ({file_size_kb:.1f} KB > 50 KB); "
            f"consider splitting into multiple agents"
        )

    # 6. nexus_roles validation
    nexus_roles = get_list_field("nexus_roles", fm_text)
    for role in nexus_roles:
        if role not in VALID_NEXUS_PHASES:
            warnings.append(
                f"WARN  {rel}: unknown nexus_roles value '{role}'. "
                f"Valid: {', '.join(sorted(VALID_NEXUS_PHASES))}"
            )

    # 7. depends_on empty check
    depends_on = get_list_field("depends_on", fm_text)
    dep_raw = get_field("depends_on", fm_text)
    if (depends_on or dep_raw) and not depends_on:
        infos.append(f"INFO  {rel}: depends_on is present but empty")

    # 8. SOUL/AGENTS header coverage
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

    # 9. Filename prefix consistency
    category = _category_for_file(filepath)
    filename = filepath.stem
    if not filename.startswith(f"{category}-"):
        warnings.append(
            f"WARN  {rel}: filename '{filename}' should start with '{category}-'"
        )

    # 10. Broken internal links
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
            warnings.append(f"WARN  {rel}: broken link '{url}' -> target not found")

    # 11. Security scan — prompt injection + hidden Unicode detection
    security_findings = scan_security(body, rel)
    for level, msg in security_findings:
        if level == "ERROR":
            errors.append(msg)
        elif level == "WARN":
            warnings.append(msg)
        else:
            infos.append(msg)

    # 12. Content freshness (> 12 months stale) — uses git
    if freshness:
        cutoff = date.today() - timedelta(days=365)
        try:
            result = subprocess.run(
                ["git", "-C", str(REPO), "log", "-1", "--format=%ad",
                 "--date=short", "--", str(filepath)],
                capture_output=True, text=True, timeout=5,
            )
            last_date_str = result.stdout.strip()
            if last_date_str:
                last_date = date.fromisoformat(last_date_str)
                if last_date < cutoff:
                    infos.append(
                        f"INFO  {rel}: last modified {last_date_str} "
                        f"(>12 months ago, may be stale)"
                    )
        except Exception:
            pass


# ── CLI ──────────────────────────────────────────────────────────────────────

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
        for _category, _rel, filepath in discover_agents():
            files.append(filepath)
    return files


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Lint The Agency agent .md files")
    parser.add_argument("files", nargs="*",
                        help="Agent file(s) to lint")
    parser.add_argument("--all", action="store_true",
                        help="Lint all agents")
    parser.add_argument("--check", action="store_true",
                        help="Alias for --all")
    parser.add_argument("--freshness", action="store_true",
                        help="Check git last-modified date (on by default; use --no-freshness to skip)")
    parser.add_argument("--no-freshness", action="store_true",
                        help="Skip git freshness check (faster)")
    args = parser.parse_args()

    if not args.files and not args.all and not args.check:
        parser.print_help()
        print("\nUsage: lint-agents.py [file ...] | --all")
        sys.exit(1)

    all_mode = args.all or args.check
    files = collect_files(args.files, all_mode)

    if not files:
        print("No agent files found.")
        sys.exit(1)

    # Freshness is on by default (matching shell behaviour); --no-freshness disables
    freshness = not args.no_freshness

    errors = []
    warnings = []
    infos = []

    print(f"Linting {len(files)} agent files...\n")

    for f in sorted(files):
        lint_file(f, errors, warnings, infos, freshness=freshness)

    # Print results with colour
    for e in errors:
        print(f"{RED}{e}{RESET}")
    for w in warnings:
        print(f"{YELLOW}{w}{RESET}")
    for i in infos:
        print(i)

    short_count = sum(1 for w in warnings if "too short" in w)

    print()
    print("=" * 40)
    print(f"Files:    {len(files)}")
    print(f"Errors:   {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Short:    {short_count} (< 100 words)")
    print("=" * 40)

    if errors:
        print(f"{RED}FAILED — fix errors before merging{RESET}")
        sys.exit(1)
    else:
        print(f"{GREEN}PASSED{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
