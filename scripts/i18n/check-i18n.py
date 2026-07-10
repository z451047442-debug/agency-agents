#!/usr/bin/env python
"""Cross-platform i18n coverage validator (canonical Python replacement for
check-i18n.sh).

Validates translation coverage and reports gaps.

Checks:
  1. Translation coverage percentage per language
  2. Untranslated agents grouped by category
  3. UTF-8 encoding validity of all agent files
  4. Template JSON generation for missing translations

Usage:
    python scripts/i18n/check-i18n.py                    # report coverage
    python scripts/i18n/check-i18n.py --lang zh          # specific language
    python scripts/i18n/check-i18n.py --strict            # fail on warnings (CI)
    python scripts/i18n/check-i18n.py --template          # output translation template
    python scripts/i18n/check-i18n.py --template --lang ja  # template for new language
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _shared import BOLD, EXCLUDE_DIRS, GREEN, RED, REPO, RESET, YELLOW  # noqa: E402

I18N_DIR = Path(__file__).resolve().parent


def ok(msg):    print(f"{GREEN}[OK]{RESET}  {msg}")
def warn(msg):  print(f"{YELLOW}[!!]{RESET}  {msg}")
def error(msg): print(f"{RED}[ERR]{RESET} {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}")


# ── agent discovery ─────────────────────────────────────────────────────────


def discover_agents():
    """Yield (category, filepath, english_name, description) for every agent."""
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        for md in sorted(entry.rglob("*.md")):
            content = md.read_text(encoding="utf-8")
            if not content.startswith("---"):
                continue
            parts = content.split("---", 2)
            if len(parts) < 3:
                continue
            fm_text = parts[1]
            name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
            desc_match = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)
            name = name_match.group(1).strip() if name_match else ""
            desc = desc_match.group(1).strip() if desc_match else ""
            if not name:
                continue
            yield entry.name, md, name, desc


# ── translation coverage ────────────────────────────────────────────────────


def load_mapping(lang="zh"):
    """Load translation mapping from agent-names-{lang}.json.

    Returns dict of {english_name: {...}} or empty dict if file missing.
    """
    map_path = I18N_DIR / f"agent-names-{lang}.json"
    if not map_path.exists():
        return {}
    with open(map_path, encoding="utf-8") as f:
        return json.load(f)


def check_coverage(lang="zh", show_untranslated=True, template=False,
                   out=sys.stdout):
    """Analyse translation coverage and optionally print report.

    ``out`` controls where the human-readable report goes (default stdout).
    When ``template=True``, callers should pass ``out=sys.stderr`` so the
    JSON template is the only thing on stdout.

    Returns (errors, warnings) counts for exit-code decisions.
    """
    def oprint(*args, **kwargs):
        kwargs.setdefault("file", out)
        print(*args, **kwargs)

    errors_count = 0
    warnings_count = 0
    mapping = load_mapping(lang)
    agent_count = 0
    has_translation = 0
    already_localized = 0  # agent whose source name is already Chinese (or target lang)
    untranslated = defaultdict(list)  # category -> list of (name, file)
    unknown_entries = []  # mapping entries with no matching agent

    # Build set of agent names for reverse lookup
    agent_names = {}
    for category, filepath, name, desc in discover_agents():
        agent_count += 1
        agent_names[name] = (name, desc, category, filepath)
        # Check if the name already appears to be localized (contains CJK)
        if _has_cjk(name):
            already_localized += 1

    for eng_name, _entry in mapping.items():
        if eng_name not in agent_names:
            unknown_entries.append(eng_name)

    # Count translations and collect untranslated
    for name, (_name_val, desc, category, filepath) in agent_names.items():
        if _has_cjk(name):
            # Already has a CJK name — we don't count it as "needing translation"
            continue
        if name in mapping:
            has_translation += 1
        else:
            untranslated[category].append((name, filepath))

    # The denominator for coverage should exclude already-localized agents
    translatable_count = agent_count - already_localized
    coverage_pct = (has_translation * 100 / translatable_count) if translatable_count else 0

    # ── report ──────────────────────────────────────────────────────────────

    if lang != "zh":
        _header(f"i18n Coverage Report — {lang}", out)
    else:
        _header("i18n Coverage Report — Chinese (zh)", out)

    oprint(f"  Total agents:          {agent_count}")
    oprint(f"  Already localized:     {already_localized} (name contains CJK characters)")
    oprint(f"  Translatable (EN):     {translatable_count}")
    if len(mapping) > 0:
        oprint(f"  Mapping entries:       {len(mapping)}")
    oprint(f"  Have translations:     {has_translation}")
    oprint(f"  Coverage:              {coverage_pct:.1f}%")
    if unknown_entries:
        oprint(f"  {YELLOW}Orphaned entries:{RESET}      {len(unknown_entries)} (in mapping but no matching agent)")
        warnings_count += 1

    # ── untranslated by category ─────────────────────────────────────────────

    if show_untranslated and untranslated:
        oprint()
        _header(f"Untranslated Agents ({len(list(_all_entries(untranslated)))} agents in "
               f"{len(untranslated)} categories)", out)
        for category in sorted(untranslated):
            agents = untranslated[category]
            oprint(f"\n  {BOLD}{category}{RESET} ({len(agents)} missing):")
            for name, filepath in sorted(agents, key=lambda x: x[0]):
                try:
                    rel = str(filepath.relative_to(REPO)).replace("\\", "/")
                except ValueError:
                    rel = str(filepath)
                oprint(f"    - {name}")
                oprint(f"      {rel}")

    # ── orphaned mapping entries ────────────────────────────────────────────

    if unknown_entries and show_untranslated:
        oprint()
        _header(f"Orphaned Mapping Entries ({len(unknown_entries)} entries "
               f"with no matching agent)", out)
        for name in sorted(unknown_entries):
            oprint(f"    - {name}")

    # ── template generation ─────────────────────────────────────────────────

    if template:
        _header(f"Translation Template ({lang})", out)
        oprint(f"Add the following entries to "
               f"{I18N_DIR / f'agent-names-{lang}.json'}:")
        oprint()
        template_obj = {}
        for category in sorted(untranslated):
            for name, _filepath in sorted(untranslated[category], key=lambda x: x[0]):
                template_obj[name] = {"name": "", "description": ""}
        json.dump(template_obj, sys.stdout, ensure_ascii=False, indent=2)
        print()  # trailing newline
        oprint(f"\n  Tip: pipe stdout to save: --template > new-entries-{lang}.json")

    return errors_count, warnings_count


def _header(msg, out=None):
    """Print a bold header to ``out`` (default stdout)."""
    dest = out or sys.stdout
    print(file=dest)
    print(f"{BOLD}{msg}{RESET}", file=dest)


def _has_cjk(text):
    """Return True if text contains Chinese/Japanese/Korean characters."""
    if not text:
        return False
    return bool(re.search(r'[一-鿿㐀-䶿豈-﫿　-〿'
                          r'＀-￯぀-ゟ゠-ヿ가-힯]',
                          text))


def _all_entries(d):
    """Flatten a {category: [(name, file), ...]} dict to total count."""
    return [item for items in d.values() for item in items]


# ── UTF-8 validation ────────────────────────────────────────────────────────


def check_encoding(out=sys.stdout):
    """Verify all agent files are valid UTF-8.

    Returns count of files with encoding issues.
    """
    def oprint(*args, **kwargs):
        kwargs.setdefault("file", out)
        print(*args, **kwargs)

    oprint()
    _header("UTF-8 Encoding Check", out)
    bad = 0
    for _category, filepath, _name, _desc in discover_agents():
        try:
            content = filepath.read_bytes().decode("utf-8")
            # Re-encode and decode to catch subtle invalid sequences
            content.encode("utf-8").decode("utf-8")
        except (UnicodeDecodeError, UnicodeEncodeError) as e:
            try:
                rel = str(filepath.relative_to(REPO)).replace("\\", "/")
            except ValueError:
                rel = str(filepath)
            error(f"Invalid UTF-8: {rel} — {e}")
            bad += 1
    if bad == 0:
        _ok(f"All {_count_agents()} agent files pass UTF-8 validation", out)
    return bad


def _ok(msg, out=None):
    """Print a green [OK] message to ``out``."""
    dest = out or sys.stdout
    print(f"{GREEN}[OK]{RESET}  {msg}", file=dest)


def _count_agents():
    return sum(1 for _ in discover_agents())


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Validate i18n translation coverage and encoding.",
    )
    parser.add_argument(
        "--lang", default="zh",
        help="Language code (default: zh, loads agent-names-zh.json).",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Treat warnings as errors (for CI).",
    )
    parser.add_argument(
        "--template", action="store_true",
        help="Output a JSON template for missing translations.",
    )
    parser.add_argument(
        "--no-untranslated", action="store_true",
        help="Suppress per-category untranslated listing.",
    )
    args = parser.parse_args()

    # Validate mapping file exists (warning, not error)
    map_path = I18N_DIR / f"agent-names-{args.lang}.json"
    if not map_path.exists():
        warn(f"Mapping file not found: {map_path}")
        if args.lang == "zh":
            warn("Create agent-names-zh.json to enable coverage tracking.")

    all_errors = 0
    all_warnings = 0

    # Run coverage check — when generating a template, send the human-readable
    # report to stderr so that stdout carries only the JSON template.
    report_out = sys.stderr if args.template else sys.stdout
    errors, warnings = check_coverage(
        lang=args.lang,
        show_untranslated=not args.no_untranslated,
        template=args.template,
        out=report_out,
    )
    all_errors += errors
    all_warnings += warnings

    # Check file encoding
    encoding_bad = check_encoding(out=report_out)
    all_errors += encoding_bad

    # ── final verdict ───────────────────────────────────────────────────────
    print(file=report_out)
    if all_errors > 0:
        print(f"{RED}FAILED:{RESET} {all_errors} error(s), {all_warnings} warning(s)",
              file=report_out)
        sys.exit(1)
    elif args.strict and all_warnings > 0:
        print(f"{RED}FAILED (strict):{RESET} {all_warnings} warning(s)",
              file=report_out)
        sys.exit(1)
    else:
        print(f"{GREEN}PASSED{RESET} ({all_warnings} warning(s))",
              file=report_out)
        sys.exit(0)


if __name__ == "__main__":
    main()
