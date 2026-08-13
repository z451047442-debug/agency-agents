#!/usr/bin/env python
"""Cross-platform agent quality scoring (canonical Python implementation).

Scores every agent on multiple quality dimensions and produces a ranked report.

Usage:
    python scripts/score-agents.py                    # all agents
    python scripts/score-agents.py --category engineering
    python scripts/score-agents.py --file path/to/agent.md
    python scripts/score-agents.py --threshold 8      # CI gate
    python scripts/score-agents.py --json              # machine-readable output

v7 dimensions (score_agent_v7, 0-18, Gate+Score architecture):
    Gate (pass/fail, fail caps grade to D):
      safeguards            (>=1): disclaimer presence, scope boundaries
      output_spec           (>=1): concrete deliverable format definitions
    Score (7 dimensions):
      content_depth          (0-6): tools + actionable density + case coverage + domain specificity
      references             (0-2): citation count + quality (inline with methodology context)
      cross_refs             (0-2): agent ecosystem linkage via depends_on
      method_decision_model  (0-3): trade-off depth (0-1.5) + decision frameworks (0-1.5)
      constraint_awareness   (0-2): explicit limitations, boundaries, when to consult experts
      collab_protocol       (0-1.5): input expectations, output specs, agent handoff interfaces
      edge_cases            (0-1.5): domain-specific pitfalls, tricky scenarios, grey areas
"""

import argparse
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

from _shared import (
    BOLD,
    CYAN,
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
from _shared.validators import (
    CORE_SECTIONS,
    CRITICAL_RISK_CATEGORIES,
    HIGH_RISK_CATEGORIES,
    git_last_modified,
)
from scoring import (
    _compute_v7_grade,
    _generate_v7_improvement_plan,
    _register_shim,
    print_json_report,
    print_terminal_report,
    score_agent,
    score_agent_v7,
)

BASELINE_FILE = REPO / ".score-baseline.json"
HISTORY_FILE = REPO / ".score-history.jsonl"

SECTION_MIN_WORDS = 30  # words required after a section header to count as "substantive"

__all__ = [
    "REPO",
    "CORE_SECTIONS",
    "CRITICAL_RISK_CATEGORIES",
    "HIGH_RISK_CATEGORIES",
    "get_body",
    "get_field",
    "get_frontmatter_text",
    "get_list_field",
    "git_last_modified",
    "score_agent",
    "score_agent_v7",
    "print_terminal_report",
    "print_json_report",
    "_compute_v7_grade",
    "_generate_v7_improvement_plan",
    "YELLOW",
]

# ── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Score The Agency agent .md files on quality (v7, 0-18 scale)")
    parser.add_argument("--category", "-c",
                        help="Score agents in a specific category only")
    parser.add_argument("--file", "-f",
                        help="Score a single agent file")
    parser.add_argument("--threshold", type=float, default=0,
                        help="Exit 1 if any agent scores below this value (CI gate)")
    parser.add_argument("--json", action="store_true",
                        help="Output machine-readable JSON")
    parser.add_argument("--out", "-o",
                        help="Write JSON output to file (avoids pipe truncation on Windows)")
    parser.add_argument("--no-freshness", action="store_true",
                        help="Skip git freshness check (faster)")
    parser.add_argument("--risk", choices=["critical", "high", "general"],
                        help="Filter by risk tier")
    parser.add_argument("--below", type=float, default=0,
                        help="Show only agents scoring below this value")
    parser.add_argument("--above", type=float, default=0,
                        help="Show only agents scoring above this value")
    parser.add_argument("--min-score", type=float, default=0,
                        help="Fail if any agent scores below this absolute floor")
    parser.add_argument("--require-safeguards", action="store_true",
                        help="Fail if any critical/high-risk agent lacks safeguards section")
    parser.add_argument("--compare",
                        help="Compare scores against a base branch (e.g. origin/main)")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Update the score baseline after this run")
    parser.add_argument("--no-baseline", action="store_true",
                        help="Skip baseline regression check")
    args = parser.parse_args()

    # --compare mode: diff scores against a base ref
    if args.compare:
        base_ref = args.compare
        import tempfile

        # Score current state
        cur_files = list(discover_agents(category_filter=args.category))
        cur_scores = {}
        for _cat, _rel, filepath in cur_files:
            r = score_agent_v7(filepath, check_freshness=False)
            r["total"] = r["v7_total"]
            r["category"] = filepath.parent.name
            cur_scores[filepath.stem] = r

        # Score base state via git show
        with tempfile.TemporaryDirectory() as tmpdir:
            base_scores = {}
            for _cat, rel, _filepath in cur_files:
                try:
                    result = subprocess.run(
                        ["git", "show", f"{base_ref}:{rel}"],
                        capture_output=True, text=True, timeout=10,
                        cwd=str(REPO),
                    )
                    if result.returncode != 0 or not result.stdout.strip():
                        base_scores[_filepath.stem] = None  # new file
                        continue
                    # Write to temp so score_agent can read it
                    tmp = Path(tmpdir) / _filepath.name
                    tmp.parent.mkdir(parents=True, exist_ok=True)
                    tmp.write_text(result.stdout, encoding="utf-8")
                    r = score_agent_v7(tmp, check_freshness=False)
                    r["total"] = r["v7_total"]
                    r["category"] = _filepath.parent.name
                    base_scores[_filepath.stem] = r
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    base_scores[_filepath.stem] = None

        # Compare
        changes = []
        for aid, cur in cur_scores.items():
            base = base_scores.get(aid)
            if base is None:
                changes.append((aid, cur["category"], cur["total"], None, cur["total"], "NEW"))
            else:
                delta = cur["total"] - base["total"]
                if delta != 0:
                    changes.append((aid, cur["category"], cur["total"], base["total"], delta,
                                    "UP" if delta > 0 else "DOWN"))

        changes.sort(key=lambda x: (x[4] > 0, abs(x[4])), reverse=True)

        print(f"\n{BOLD}Score Trend: HEAD vs {base_ref}{RESET}")
        up = sum(1 for c in changes if c[5] == "UP")
        down = sum(1 for c in changes if c[5] == "DOWN")
        new = sum(1 for c in changes if c[5] == "NEW")
        if changes:
            net = sum(c[4] for c in changes if isinstance(c[4], (int, float)))
            net_str = f"+{net}" if net > 0 else str(net)
            print(f"  {GREEN}{up} up{RESET}  {RED}{down} down{RESET}  {new} new  net: {net_str}")
        else:
            print("  No score changes detected")
            sys.exit(0)

        # Show top changes
        ups = [c for c in changes if c[5] == "UP"][:8]
        downs = [c for c in changes if c[5] == "DOWN"][:8]

        if ups:
            print(f"\n{GREEN}Score Improvements:{RESET}")
            for aid, cat, cur, base, delta, _ in ups:
                print(f"  {GREEN}+{delta}{RESET}  {aid} ({cat}): {base} -> {cur}/18")

        if downs:
            print(f"\n{RED}Score Regressions:{RESET}")
            for aid, cat, cur, base, delta, _ in downs:
                print(f"  {RED}{delta}{RESET}  {aid} ({cat}): {base} -> {cur}/18")

        if new:
            print(f"\n{CYAN}New agents (no base score):{RESET} {new}")
        sys.exit(0 if down == 0 else 1)

    # Collect files
    if args.file:
        filepath = Path(args.file)
        if not filepath.is_absolute():
            filepath = REPO / filepath
        if not filepath.exists():
            print(f"ERROR: file not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        try:
            rel = str(filepath.relative_to(REPO))
        except ValueError:
            rel = filepath.name
        files = [(filepath.parent.name, rel, filepath)]
    else:
        files = list(discover_agents(category_filter=args.category))

    if not files:
        print("No agent files found.", file=sys.stderr)
        sys.exit(1)

    # Score all with v7 (canonical scoring engine, 0-18 scale)
    results = []
    for _category, _rel, filepath in files:
        r = score_agent_v7(filepath, check_freshness=not args.no_freshness)
        # Normalize v7 fields into top-level result keys for filter/display compat
        r["total"] = r["v7_total"]
        r["grade"] = r["v7_grade"]
        r["scores"] = r["v7_scores"]
        r["risk_tier"] = r.get("v7_risk_tier", "general")
        r["issues"] = [p.get("action", str(p)) for p in r.get("v7_improvement_plan", [])]
        r["word_count"] = r.get("v7_word_count", 0)
        r["safeguard_signals"] = r.get("v7_safeguard_signals", 0)
        r["reference_signals"] = r.get("v7_reference_signals", 0)
        results.append(r)

    # Snapshot full results before any filtering (for baseline + history)
    all_totals = [r["total"] for r in results]
    all_grades = defaultdict(int)
    for r in results:
        all_grades[r["grade"]] += 1
    all_results = list(results)  # unfiltered set — CI gates must see every agent

    score_key = "total"
    if args.risk:
        results = [r for r in results if r.get("risk_tier") == args.risk]
    if args.below > 0:
        results = [r for r in results if r[score_key] < args.below]
    if args.above > 0:
        results = [r for r in results if r[score_key] > args.above]

    if not results:
        print("No agents match the filter criteria.", file=sys.stderr)
        sys.exit(0)

    # Report
    if args.json:
        print_json_report(results, out_path=args.out)
    else:
        print_terminal_report(results, args)

    # CI gate: safeguard check (professional-advice categories must have disclaimers)
    if args.require_safeguards:
        SAFEGUARD_REQUIRED = {
            "healthcare", "pharma-biotech", "legal", "finance", "insurance", "securities",
        }
        no_safeguard = [
            r for r in all_results
            if (r["category"] in SAFEGUARD_REQUIRED
                and r.get("safeguard_signals", 0) == 0)
        ]
        if no_safeguard:
            print(
                f"SAFEGUARD FAIL: {len(no_safeguard)} critical/high-risk agent(s) "
                f"missing safeguards section",
                file=sys.stderr,
            )
            for r in sorted(no_safeguard, key=lambda x: x["id"])[:20]:
                print(f"  {r['id']} ({r['category']})", file=sys.stderr)
            if len(no_safeguard) > 20:
                print(f"  ... and {len(no_safeguard) - 20} more", file=sys.stderr)
            sys.exit(1)

    # CI gate: per-agent threshold (changed agents must meet bar)
    if args.threshold is not None and args.threshold > 0:
        below = [r for r in all_results if r["total"] < args.threshold]
        if below:
            print(f"THRESHOLD FAIL: {len(below)} agent(s) below {args.threshold}",
                  file=sys.stderr)
            sys.exit(1)

    # CI gate: absolute floor (no agent may fall below this, period)
    if args.min_score is not None and args.min_score > 0:
        below_floor = [r for r in all_results if r["total"] < args.min_score]
        if below_floor:
            print(
                f"FLOOR FAIL: {len(below_floor)} agent(s) below absolute floor"
                f" of {args.min_score}",
                file=sys.stderr,
            )
            for r in sorted(below_floor, key=lambda x: x["total"])[:10]:
                print(f"  {r['total']}/18  {r['id']} ({r['category']})", file=sys.stderr)
            if len(below_floor) > 10:
                print(f"  ... and {len(below_floor) - 10} more", file=sys.stderr)
            sys.exit(1)

    # ── Baseline regression gate ──────────────────────────────────────────────
    if not args.no_baseline and all_totals and not args.file:
        current = {
            "date": date.today().isoformat(),
            "total_agents": len(all_totals),
            "mean_score": round(statistics.mean(all_totals), 2),
            "median_score": round(statistics.median(all_totals), 1),
            "a_pct": round((all_grades.get("A", 0) + all_grades.get("B", 0)) / len(all_totals) * 100, 1),
            "d_count": all_grades.get("D", 0),
        }
        # Append to history JSONL (LF newlines — repo enforces eol=lf)
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HISTORY_FILE, "a", encoding="utf-8", newline="\n") as hf:
            json.dump(current, hf, ensure_ascii=False)
            hf.write("\n")

        # Accept the current state before the gate compares against it.
        if args.update_baseline:
            with open(BASELINE_FILE, "w", encoding="utf-8", newline="\n") as bf:
                json.dump(current, bf, indent=2, ensure_ascii=False)
                bf.write("\n")
            print(f"{GREEN}Baseline updated: {BASELINE_FILE}{RESET}",
                  file=sys.stderr)

        if BASELINE_FILE.exists():
            with open(BASELINE_FILE, encoding="utf-8") as bf:
                baseline = json.load(bf)
            regressions = []
            if current["total_agents"] < baseline.get("total_agents", 0):
                regressions.append(f"agent count {baseline['total_agents']} → {current['total_agents']}")
            if current["mean_score"] < baseline.get("mean_score", 0) - 0.1:
                regressions.append(f"mean score {baseline['mean_score']} → {current['mean_score']}")
            if current["a_pct"] < baseline.get("a_pct", 0) - 2:
                regressions.append(f"A+B% {baseline['a_pct']}% → {current['a_pct']}%")
            if regressions:
                print(f"\n{RED}BASELINE REGRESSION:{RESET}", file=sys.stderr)
                for r in regressions:
                    print(f"  - {r}", file=sys.stderr)
                print("  Run --update-baseline if this is expected.", file=sys.stderr)
                sys.exit(1)
            else:
                improved = []
                if current["mean_score"] > baseline.get("mean_score", 0) + 0.1:
                    improved.append(f"mean +{current['mean_score'] - baseline['mean_score']:.2f}")
                if current["a_pct"] > baseline.get("a_pct", 0) + 2:
                    improved.append(f"A+B% +{current['a_pct'] - baseline['a_pct']:.1f}%")
                if improved:
                    print(f"{GREEN}Baseline improved: {', '.join(improved)}{RESET}",
                          file=sys.stderr)

    try:
        from telemetry import record_event
        record_event("score", category=args.category)
    except (ImportError, AttributeError):
        pass  # telemetry is optional
    sys.exit(0)


_register_shim(globals())

if __name__ == "__main__":
    main()
