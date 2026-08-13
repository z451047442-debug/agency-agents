"""Terminal and JSON report generators for score results."""

import json
import statistics
import sys
from collections import defaultdict
from datetime import date

from _shared import BOLD, CYAN, GREEN, RED, RESET, YELLOW

# ── report generators ────────────────────────────────────────────────────────

def print_terminal_report(results, args):
    """Human-readable terminal report with distribution statistics."""
    total_agents = len(results)
    if total_agents == 0:
        print(f"\n{BOLD}=== Agent Quality Report v2 ==={RESET}")
        print("Total: 0 agents")
        return

    # v7 is the canonical scoring engine (0-18 scale)
    version_label, score_field, grade_field = "v7", "total", "grade"

    grades = defaultdict(int)
    scores_by_cat = defaultdict(list)
    all_totals = []

    for r in results:
        grades[r.get("grade", "?")] += 1
        scores_by_cat[r["category"]].append(r["total"])
        all_totals.append(r["total"])

    # Header
    print(f"\n{BOLD}=== Agent Quality Report ({version_label}) ==={RESET}")
    print(f"Total: {total_agents} agents")
    if args.category:
        print(f"Category: {args.category}")
    print()

    # Distribution statistics
    mean_score = statistics.mean(all_totals)
    std_score = statistics.stdev(all_totals) if len(all_totals) > 1 else 0.0
    sorted_scores = sorted(all_totals)
    q1 = sorted_scores[len(sorted_scores) // 4]
    q2 = sorted_scores[len(sorted_scores) // 2]
    q3 = sorted_scores[len(sorted_scores) * 3 // 4]

    print(f"{BOLD}Distribution:{RESET}")
    print(f"  Mean: {mean_score:.1f}  StdDev: {std_score:.2f}  "
          f"Q1={q1}  Median={q2}  Q3={q3}")
    # Spread quality: target std ≥ 1.2 for healthy discrimination
    if std_score >= 1.5:
        spread_label = f"{GREEN}excellent{RESET}"
    elif std_score >= 1.0:
        spread_label = f"{CYAN}adequate{RESET}"
    elif std_score >= 0.5:
        spread_label = f"{YELLOW}weak{RESET}"
    else:
        spread_label = f"{RED}critical — scores are near-identical{RESET}"
    print(f"  Spread: {spread_label} (StdDev {std_score:.2f})")
    print()

    # Grade distribution with bars
    print(f"{BOLD}Score Distribution:{RESET}")
    for grade, label, color in [("A", "A (≥12.5)", GREEN), ("B", "B (10-12)", CYAN),
                                  ("C", "C (8-10)", YELLOW), ("D", "D (<8)", RED)]:
        count = grades.get(grade, 0)
        pct = (count / total_agents * 100) if total_agents else 0
        bar = "█" * int(round(pct / 2))
        print(f"  {color}{label:<12}{RESET} {count:>4} ({pct:>5.1f}%)  {bar}")

    ab_total = grades.get("A", 0) + grades.get("B", 0)
    ab_pct = (ab_total / total_agents * 100) if total_agents else 0
    print()

    # Quality gate
    if ab_pct >= 40:
        print(f"{GREEN}═══ PASS: Quality gate met ({ab_pct:.0f}% agents grade A/B){RESET}")
    else:
        print(f"{RED}═══ FAIL: Quality gate not met ({ab_pct:.0f}% agents grade A/B, need ≥40%){RESET}")
    print()

    # Risk tier summary
    risk_dist = defaultdict(int)
    for r in results:
        risk_dist[r.get("risk_tier", "general")] += 1
    if risk_dist:
        print(f"{BOLD}Risk Tier Distribution:{RESET}")
        for tier, color in [("critical", RED), ("high", YELLOW), ("general", GREEN)]:
            count = risk_dist.get(tier, 0)
            if count:
                pct = count / total_agents * 100
                print(f"  {color}{tier:<12}{RESET} {count:>4} ({pct:5.1f}%)")
        print()

    # Top 10
    print(f"{BOLD}Top 10 Highest Scoring:{RESET}")
    top = sorted(results, key=lambda r: (-r.get(score_field, r.get("total", 0)), r["id"]))[:10]
    for i, r in enumerate(top, 1):
        detail = ", ".join(f"{k}={v}" for k, v in r.get(f"{version_label}_scores", r.get("scores", {})).items())
        display_total = r.get(score_field, r.get("total", 0))
        display_grade = r.get(grade_field, r.get("grade", "?"))
        print(f"  {i:>2}. {GREEN}{r['id']}{RESET} ({display_total} {display_grade}) — {r['category']}")
        print(f"      {detail} | {r.get('word_count', 0)} words")

    print()

    # Bottom 10
    print(f"{BOLD}Bottom 10 Lowest Scoring:{RESET}")
    bottom = sorted(results, key=lambda r: (r.get(score_field, r.get("total", 0)), r["id"]))[:10]
    risk_field = score_field.replace("total", "risk_tier") if score_field != "total" else "risk_tier"
    for i, r in enumerate(bottom, 1):
        detail = ", ".join(f"{k}={v}" for k, v in r.get(f"{version_label}_scores", r.get("scores", {})).items())
        issues = "; ".join(r.get("issues", [])[:3])
        display_total = r.get(score_field, r.get("total", 0))
        display_grade = r.get(grade_field, r.get("grade", "?"))
        risk_tier_val = r.get(risk_field, r.get("risk_tier", "general"))
        risk = f" [{risk_tier_val}]" if risk_tier_val != "general" else ""
        print(f"  {i:>2}. {RED}{r['id']}{RESET} ({display_total} {display_grade}) — {r['category']}{risk}")
        print(f"      {detail} | {r.get('word_count', 0)} words  "
              f"safe={r.get('safeguard_signals', 0)}  ref={r.get('reference_signals', 0)}")
        if issues:
            print(f"      {YELLOW}{issues}{RESET}")

    print()

    # Category averages
    print(f"{BOLD}Category Averages:{RESET}")
    for cat in sorted(scores_by_cat.keys()):
        scores = scores_by_cat[cat]
        avg = sum(scores) / len(scores)
        a_count = sum(1 for r in results if r.get("category") == cat and r.get("grade") == "A")
        b_count = sum(1 for r in results if r.get("category") == cat and r.get("grade") == "B")
        c_count = sum(1 for r in results if r.get("category") == cat and r.get("grade") == "C")
        d_count = sum(1 for r in results if r.get("category") == cat and r.get("grade") == "D")
        print(f"  {cat:<30} avg {avg:.1f}  ({len(scores)} agents, "
              f"{GREEN}{a_count}A{RESET} / {b_count}B / {c_count}C / {RED}{d_count}D{RESET})")

    print()

    # Perimeter stats. stale/broken/thin are v1-engine-only metrics (v7 results
    # don't carry them); derive each stat only from fields present in the
    # result set so v7 runs don't report bogus zeros or full-roster counts.
    _V1_FIELDS = ("days_since_modified", "broken_links", "substantive_sections")
    has_v1_fields = any(k in r for r in results for k in _V1_FIELDS)
    short = sum(1 for r in results if r.get("word_count", 0) < 100)
    no_safe = sum(1 for r in results if r.get("safeguard_signals", 0) == 0)
    no_ref = sum(1 for r in results if r.get("reference_signals", 0) == 0)
    critical_low = sum(
        1 for r in results
        if r.get("risk_tier") == "critical"
        and r.get("scores", {}).get("content_depth", 0) < 2
    )
    print(f"Perimeter: {RED}{short} short{RESET} (<100w) | "
          f"{RED}{no_safe} no safeguards{RESET} | "
          f"{YELLOW}{no_ref} no references{RESET}")
    if has_v1_fields:
        stale = sum(1 for r in results if r.get("days_since_modified", 0) > 365)
        broken = sum(1 for r in results if r.get("broken_links", 0) > 0)
        thin = sum(1 for r in results if r.get("substantive_sections", 0) < 4)
        print(f"          {YELLOW}{thin} thin{RESET} (<4 substantive sections) | "
              f"{YELLOW}{stale} stale{RESET} (>1yr) | "
              f"{YELLOW}{broken} broken links{RESET}")
    if critical_low:
        print(f"  {RED}[!] {critical_low} critical-risk agents with insufficient content depth{RESET}")

    # Threshold check
    if args.threshold is not None:
        below = [r for r in results if r["total"] < args.threshold]
        if below:
            print(f"\n{RED}THRESHOLD FAIL: {len(below)} agent(s) scored below {args.threshold}{RESET}")
        else:
            print(f"\n{GREEN}THRESHOLD PASS: all agents score ≥ {args.threshold}{RESET}")


def print_json_report(results, out_path=None):
    """Machine-readable JSON output with distribution statistics."""
    all_totals = [r["total"] for r in results]
    output = {
        "generated": str(date.today()),
        "total_agents": len(results),
        "grade_distribution": {},
        "distribution": {
            "mean": round(statistics.mean(all_totals), 2) if all_totals else 0,
            "stddev": round(statistics.stdev(all_totals), 2) if len(all_totals) > 1 else 0,
            "q1": sorted(all_totals)[len(all_totals) // 4] if all_totals else 0,
            "median": sorted(all_totals)[len(all_totals) // 2] if all_totals else 0,
            "q3": sorted(all_totals)[len(all_totals) * 3 // 4] if all_totals else 0,
        },
        "agents": [],
    }

    grades = defaultdict(int)
    for r in results:
        grades[r["grade"]] += 1
        agent_entry = {
            "id": r["id"],
            "category": r["category"],
            "path": r["path"],
            "total": r["total"],
            "grade": r["grade"],
            "risk_tier": r.get("risk_tier", "general"),
            "scores": r["scores"],
            "word_count": r.get("word_count", 0),
            "sections_found": r.get("sections_found", 0),
            "substantive_sections": r.get("substantive_sections", 0),
            "domain_signals": r.get("domain_signals", 0),
            "actionable_count": r.get("actionable_count", 0),
            "tool_references": r.get("tool_references", 0),
            "case_examples": r.get("case_examples", 0),
            "boilerplate_count": r.get("boilerplate_count", 0),
            "safeguard_signals": r.get("safeguard_signals", 0),
            "reference_signals": r.get("reference_signals", 0),
            "file_size_kb": r.get("file_size_kb", 0),
            "issues": r.get("issues", []),
            "last_modified": r.get("last_modified"),
            "v7_gate_passed": r.get("v7_gate_passed"),
            "v7_gate_failures": r.get("v7_gate_failures", []),
        }
        output["agents"].append(agent_entry)

    output["grade_distribution"] = dict(grades)
    output["quality_gate"] = (
        "PASS" if (grades.get("A", 0) + grades.get("B", 0)) / len(results) >= 0.4
        else "FAIL"
    )

    json_str = json.dumps(output, indent=2, ensure_ascii=False)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(json_str)
            f.write("\n")
    else:
        sys.stdout.write(json_str)
        sys.stdout.write("\n")
        sys.stdout.flush()
