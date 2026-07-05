#!/usr/bin/env python
"""Cross-platform agent quality scoring (canonical Python implementation).

Scores every agent on multiple quality dimensions and produces a ranked report.
Replaces the shell-based score-agents.sh with enhanced metrics.

Usage:
    python scripts/score-agents.py                    # all agents
    python scripts/score-agents.py --category engineering
    python scripts/score-agents.py --file path/to/agent.md
    python scripts/score-agents.py --threshold 5      # CI gate (exit 1 if any <5)
    python scripts/score-agents.py --json              # machine-readable output
    python scripts/score-agents.py --json --category cybersecurity

Scoring dimensions (0-10 total):
    Content Depth    (0-3): word count tiers
    Structure        (0-3): section completeness
    Frontmatter      (0-2): metadata richness
    File Health      (0-2): appropriate file size + freshness + link health
"""

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {
    ".git", ".github", ".vs", ".vscode", ".claude",
    ".pytest_cache", "examples", "integrations",
    "scripts", "docs", "schemas", "tests",
    "__pycache__", "env", "node_modules",
}

# Sections that indicate a well-structured agent
CORE_SECTIONS = {
    "Identity":       r"(?:identity|🧠.*identity|your identity|who you are)",
    "Core Mission":   r"(?:core\s*mission|🎯.*mission|your core mission|what you do)",
    "Critical Rules": r"(?:critical\s*rules?|🚨.*rules?|rules?\s*you\s*must\s*follow|non-negotiables?)",
    "Deliverables":   r"(?:deliverable|📦.*deliverable|what you produce)",
    "Workflow":       r"(?:workflow|process|🔄.*workflow|how you work|your workflow)",
    "Success Metrics": r"(?:success\s*metrics|🎯.*metrics|metrics\s*[—\-]|how you measure)",
    "Communication":  r"(?:communication\s*style|💬.*communication|how you communicate|tone)",
}


def _supports_color():
    return (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
            and not os.environ.get("NO_COLOR")
            and os.environ.get("TERM", "") != "dumb")


if _supports_color():
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    RED = "\033[0;31m"
    BOLD = "\033[1m"
    CYAN = "\033[0;36m"
    RESET = "\033[0m"
else:
    GREEN = YELLOW = RED = BOLD = CYAN = RESET = ""


# ── helpers ──────────────────────────────────────────────────────────────────

def get_frontmatter_text(content):
    parts = content.split("---", 2)
    return parts[1] if len(parts) >= 3 else ""


def get_body(content):
    parts = content.split("---", 2)
    return parts[2] if len(parts) >= 3 else ""


def get_field(field, fm_text):
    m = re.search(rf"^{re.escape(field)}:\s*(.+)$", fm_text, re.MULTILINE)
    return m.group(1).strip() if m else ""


def discover_agents(category_filter=None):
    """Yield (category, rel_path, file_path) for every agent .md file."""
    for entry in sorted(REPO.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if entry.name in EXCLUDE_DIRS:
            continue
        if category_filter and entry.name != category_filter:
            continue
        for md in sorted(entry.rglob("*.md")):
            try:
                rel = str(md.relative_to(REPO)).replace("\\", "/")
            except ValueError:
                rel = md.name
            yield entry.name, rel, md


def git_last_modified(filepath):
    """Return last git commit date as a date object, or None."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO), "log", "-1", "--format=%ad",
             "--date=short", "--", str(filepath)],
            capture_output=True, text=True, timeout=5,
        )
        last_date_str = result.stdout.strip()
        if last_date_str:
            return date.fromisoformat(last_date_str)
    except Exception:
        pass
    return None


# ── scoring engine ───────────────────────────────────────────────────────────

def score_agent(filepath, check_freshness=True):
    """Score a single agent file. Returns dict with scores and metadata."""
    filepath = Path(filepath)
    try:
        rel = str(filepath.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        rel = filepath.name

    result = {
        "id": filepath.stem,
        "category": filepath.parent.name,
        "path": rel,
        "scores": {},
        "total": 0,
        "grade": "D",
        "issues": [],
    }

    if not filepath.is_file():
        result["issues"].append("file not found")
        return result

    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        result["issues"].append("cannot read file (encoding?)")
        return result

    fm_text = get_frontmatter_text(content)
    body = get_body(content)

    # ── Dimension 1: Content Depth (0-3) ──
    word_count = len(body.split())
    if word_count >= 800:
        wc_score = 3
    elif word_count >= 400:
        wc_score = 2
    elif word_count >= 100:
        wc_score = 1
    else:
        wc_score = 0
        result["issues"].append(f"too short ({word_count} words, need ≥100)")

    result["scores"]["content_depth"] = wc_score
    result["word_count"] = word_count

    # ── Dimension 2: Structure Completeness (0-3) ──
    sections_found = 0
    for section, pattern in CORE_SECTIONS.items():
        if re.search(pattern, body, re.IGNORECASE):
            sections_found += 1
        else:
            result["issues"].append(f"missing section: {section}")

    if sections_found >= 7:
        sec_score = 3
    elif sections_found >= 5:
        sec_score = 2
    elif sections_found >= 3:
        sec_score = 1
    else:
        sec_score = 0

    result["scores"]["structure"] = sec_score
    result["sections_found"] = sections_found

    # ── Dimension 3: Frontmatter Richness (0-2) ──
    fm_score = 0
    fm_checks = []

    description = get_field("description", fm_text)
    if description:
        desc_len = len(description)
        if desc_len >= 80:
            fm_score += 0.5
        elif desc_len >= 30:
            fm_score += 0.25
        fm_checks.append(f"description ({desc_len} chars)")
    else:
        fm_checks.append("missing description")

    if get_field("emoji", fm_text):
        fm_score += 0.5
    else:
        fm_checks.append("missing emoji")

    if get_field("color", fm_text):
        fm_score += 0.5
    else:
        fm_checks.append("missing color")

    if get_field("vibe", fm_text):
        fm_score += 0.25
        fm_checks.append("has vibe")

    nexus_roles_text = get_field("nexus_roles", fm_text)
    if nexus_roles_text:
        fm_score += 0.25
        fm_checks.append("has nexus_roles")

    fm_score = min(round(fm_score * 2), 2)  # scale to 0-2

    result["scores"]["frontmatter"] = fm_score
    result["frontmatter_details"] = fm_checks

    # ── Dimension 4: File Health (0-2) ──
    health_score = 0

    # 4a. File size sweet spot (2-8 KB ideal)
    file_size_kb = len(content.encode("utf-8")) / 1024
    if 2 <= file_size_kb <= 8:
        health_score += 1.0
    elif 1 <= file_size_kb <= 12:
        health_score += 0.5
    else:
        result["issues"].append(f"file size out of range ({file_size_kb:.1f} KB)")

    result["file_size_kb"] = round(file_size_kb, 1)

    # 4b. No broken internal links
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+\.md)\)")
    file_dir = filepath.parent
    broken_links = 0
    for m in link_pattern.finditer(body):
        url = m.group(2)
        if url.startswith("http://") or url.startswith("https://"):
            continue
        if url.startswith("/"):
            target = REPO / url.lstrip("/")
        else:
            target = (file_dir / url).resolve()
        if not target.exists():
            broken_links += 1

    if broken_links == 0:
        health_score += 0.5
    else:
        result["issues"].append(f"{broken_links} broken internal link(s)")

    # 4c. Freshness (modified within 12 months)
    if check_freshness:
        last_mod = git_last_modified(filepath)
        if last_mod:
            days_ago = (date.today() - last_mod).days
            if days_ago <= 180:
                health_score += 0.5
            elif days_ago <= 365:
                health_score += 0.25
            else:
                result["issues"].append(f"stale ({days_ago} days since last change)")
            result["last_modified"] = str(last_mod)
            result["days_since_modified"] = days_ago

    health_score = min(round(health_score * 2), 2)  # scale to 0-2

    result["scores"]["file_health"] = health_score
    result["broken_links"] = broken_links

    # ── Total & Grade ──
    total = wc_score + sec_score + fm_score + health_score
    if total >= 8:
        grade = "A"
    elif total >= 5:
        grade = "B"
    elif total >= 3:
        grade = "C"
    else:
        grade = "D"

    result["total"] = total
    result["grade"] = grade

    return result


# ── report generators ────────────────────────────────────────────────────────

def print_terminal_report(results, args):
    """Human-readable terminal report."""
    total_agents = len(results)
    grades = defaultdict(int)
    scores_by_cat = defaultdict(list)

    for r in results:
        grades[r["grade"]] += 1
        scores_by_cat[r["category"]].append(r["total"])

    # Header
    print(f"\n{BOLD}=== Agent Quality Report ==={RESET}")
    print(f"Total: {total_agents} agents")
    if args.category:
        print(f"Category: {args.category}")
    print()

    # Grade distribution with bars
    print(f"{BOLD}Score Distribution:{RESET}")
    for grade, label, color in [("A", "A (8-10)", GREEN), ("B", "B (5-7)", CYAN),
                                  ("C", "C (3-4)", YELLOW), ("D", "D (0-2)", RED)]:
        count = grades.get(grade, 0)
        pct = (count / total_agents * 100) if total_agents else 0
        bar = "█" * int(round(pct / 2))
        print(f"  {color}{label:<12}{RESET} {count:>4} ({pct:>5.1f}%)  {bar}")

    ab_total = grades.get("A", 0) + grades.get("B", 0)
    ab_pct = (ab_total / total_agents * 100) if total_agents else 0
    print()

    # Quality gate
    if ab_pct >= 60:
        print(f"{GREEN}═══ PASS: Quality gate met ({ab_pct:.0f}% agents grade A/B){RESET}")
    else:
        print(f"{RED}═══ FAIL: Quality gate not met ({ab_pct:.0f}% agents grade A/B, need ≥60%){RESET}")
    print()

    # Top 10
    print(f"{BOLD}Top 10 Highest Scoring:{RESET}")
    top = sorted(results, key=lambda r: (-r["total"], r["id"]))[:10]
    for i, r in enumerate(top, 1):
        detail = ", ".join(f"{k}={v}" for k, v in r["scores"].items())
        print(f"  {i:>2}. {GREEN}{r['id']}{RESET} ({r['total']}/10 {r['grade']}) — {r['category']}")
        print(f"      {detail} | {r['word_count']} words")

    print()

    # Bottom 10
    print(f"{BOLD}Bottom 10 Lowest Scoring:{RESET}")
    bottom = sorted(results, key=lambda r: (r["total"], r["id"]))[:10]
    for i, r in enumerate(bottom, 1):
        issues = "; ".join(r["issues"][:3])
        print(f"  {i:>2}. {RED}{r['id']}{RESET} ({r['total']}/10 {r['grade']}) — {r['category']}")
        if issues:
            print(f"      {YELLOW}{issues}{RESET}")

    print()

    # Category averages
    print(f"{BOLD}Category Averages:{RESET}")
    for cat in sorted(scores_by_cat.keys()):
        scores = scores_by_cat[cat]
        avg = sum(scores) / len(scores)
        a_count = sum(1 for s in scores if s >= 8)
        d_count = sum(1 for s in scores if s <= 2)
        print(f"  {cat:<30} avg {avg:.1f}  ({len(scores)} agents, "
              f"{GREEN}{a_count}A{RESET} / {RED}{d_count}D{RESET})")

    print()

    # Perimeter stats
    short = sum(1 for r in results if r["word_count"] < 100)
    stale = sum(1 for r in results if r.get("days_since_modified", 0) > 365)
    broken = sum(1 for r in results if r.get("broken_links", 0) > 0)
    print(f"Perimeter: {RED}{short} short{RESET} (<100w) | "
          f"{YELLOW}{stale} stale{RESET} (>1yr) | "
          f"{YELLOW}{broken} broken links{RESET}")

    # Threshold check
    if args.threshold is not None:
        below = [r for r in results if r["total"] < args.threshold]
        if below:
            print(f"\n{RED}THRESHOLD FAIL: {len(below)} agent(s) scored below {args.threshold}{RESET}")
        else:
            print(f"\n{GREEN}THRESHOLD PASS: all agents score ≥ {args.threshold}{RESET}")


def print_json_report(results):
    """Machine-readable JSON output."""
    output = {
        "generated": str(date.today()),
        "total_agents": len(results),
        "grade_distribution": {},
        "agents": [],
    }

    grades = defaultdict(int)
    for r in results:
        grades[r["grade"]] += 1
        output["agents"].append({
            "id": r["id"],
            "category": r["category"],
            "path": r["path"],
            "total": r["total"],
            "grade": r["grade"],
            "scores": r["scores"],
            "word_count": r["word_count"],
            "sections_found": r.get("sections_found", 0),
            "file_size_kb": r.get("file_size_kb", 0),
            "issues": r["issues"],
            "last_modified": r.get("last_modified"),
        })

    output["grade_distribution"] = dict(grades)
    output["quality_gate"] = (
        "PASS" if (grades.get("A", 0) + grades.get("B", 0)) / len(results) >= 0.6
        else "FAIL"
    )

    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Score The Agency agent .md files on quality (0-10 scale)")
    parser.add_argument("--category", "-c",
                        help="Score agents in a specific category only")
    parser.add_argument("--file", "-f",
                        help="Score a single agent file")
    parser.add_argument("--threshold", type=int, default=0,
                        help="Exit 1 if any agent scores below this value (CI gate)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--no-freshness", action="store_true",
                        help="Skip git freshness check (faster)")
    args = parser.parse_args()

    # Collect files
    if args.file:
        filepath = Path(args.file)
        if not filepath.is_absolute():
            filepath = REPO / filepath
        if not filepath.exists():
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        files = [(filepath.parent.name, str(filepath.relative_to(REPO)), filepath)]
    else:
        files = list(discover_agents(category_filter=args.category))

    if not files:
        print("No agent files found.", file=sys.stderr)
        sys.exit(1)

    # Score all
    results = []
    for category, rel, filepath in files:
        r = score_agent(filepath, check_freshness=not args.no_freshness)
        results.append(r)

    # Report
    if args.json:
        print_json_report(results)
    else:
        print_terminal_report(results, args)

    # CI gate
    if args.threshold is not None and args.threshold > 0:
        below = [r for r in results if r["total"] < args.threshold]
        if below:
            print(f"THRESHOLD FAIL: {len(below)} agent(s) below {args.threshold}",
                  file=sys.stderr)
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
