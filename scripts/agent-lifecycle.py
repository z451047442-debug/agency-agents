#!/usr/bin/env python
"""Agent lifecycle management — tracks each agent through draft→review→published→deprecated.

Adds and manages a ``lifecycle`` field in agent YAML frontmatter. Agents without
this field are treated as ``published`` (backward compatible).

Lifecycle states:
    draft      — agent is being written, not ready for use
    review     — content complete, awaiting domain-expert review
    published  — reviewed and ready for production use (default)
    deprecated — no longer maintained, may be removed in a future release

Usage:
    python scripts/agent-lifecycle.py --report                    # portfolio overview
    python scripts/agent-lifecycle.py --report --category engineering
    python scripts/agent-lifecycle.py --agent <id> --status       # check state
    python scripts/agent-lifecycle.py --agent <id> --transition review  # change state
    python scripts/agent-lifecycle.py --agent <id> --transition published --note "Reviewed by SME"
    python scripts/agent-lifecycle.py --category manufacturing --transition review  # batch
    python scripts/agent-lifecycle.py --sync                      # add lifecycle field to agents missing it
    python scripts/agent-lifecycle.py --sync --dry-run            # preview what --sync would do
    python scripts/agent-lifecycle.py --find-stale --months 12    # find agents not updated in 12+ months
    python scripts/agent-lifecycle.py --json                      # machine-readable output
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
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
    get_field,
    get_frontmatter_text,
    load_module,
)

_SCRIPTS = Path(__file__).resolve().parent
_score_agents = load_module("score_agents", _SCRIPTS / "score-agents.py")
git_last_modified = _score_agents.git_last_modified

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]

LIFECYCLE_STATES = ("draft", "review", "published", "deprecated")
VALID_TRANSITIONS = {
    "draft":      ("review", "deprecated"),
    "review":     ("published", "draft"),       # can send back to draft for rework
    "published":  ("deprecated", "draft"),       # can deprecate or un-publish
    "deprecated": ("published", "draft"),        # can revive
}

STATE_COLORS = {
    "draft":      YELLOW,
    "review":     CYAN,
    "published":  GREEN,
    "deprecated": RED,
}


def get_current_lifecycle(filepath):
    """Read the lifecycle field from an agent's frontmatter. Returns 'published' if absent."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return "unknown"
    fm = get_frontmatter_text(content)
    val = get_field("lifecycle", fm)
    if val in LIFECYCLE_STATES:
        return val
    return "published"  # default for agents without the field


def set_lifecycle(filepath, new_state, note=""):
    """Update or add the lifecycle field in an agent's YAML frontmatter."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return False, str(e)

    fm = get_frontmatter_text(content)
    current = get_field("lifecycle", fm)

    if current == new_state:
        return True, f"already in '{new_state}'"

    if current in VALID_TRANSITIONS and new_state not in VALID_TRANSITIONS.get(current, ()):
        return False, f"invalid transition: '{current}' → '{new_state}'. Valid: {VALID_TRANSITIONS.get(current, ())}"

    # Check if lifecycle field already exists
    if "\nlifecycle:" in fm or fm.startswith("lifecycle:"):
        # Update existing field
        new_fm = re.sub(
            r"^lifecycle:\s*.*$",
            f"lifecycle: {new_state}",
            fm,
            flags=re.MULTILINE,
        )
    else:
        # Add after date_added or version line, or at end of frontmatter
        lines = fm.split("\n")
        insert_after = None
        for i, line in enumerate(lines):
            if re.match(r"^\s*date_added:", line):
                insert_after = i
                break
        if insert_after is None:
            for i, line in enumerate(lines):
                if re.match(r"^\s*version:", line):
                    insert_after = i
                    break

        if insert_after is not None:
            lines.insert(insert_after + 1, f"lifecycle: {new_state}")
        else:
            lines.append(f"lifecycle: {new_state}")
        new_fm = "\n".join(lines)

    new_content = content.replace(fm, new_fm, 1)

    try:
        filepath.write_text(new_content, encoding="utf-8")
        return True, f"'{current}' → '{new_state}'"
    except Exception as e:
        return False, str(e)


def discover_all_agents(category_filter=None):
    """Yield (filepath, agent_id, category) for all agents."""
    for category, _rel, filepath in discover_agents(category_filter=category_filter):
        yield filepath, filepath.stem, category


def build_lifecycle_report(category_filter=None, check_freshness=True):
    """Build full lifecycle report for all agents."""
    agents = defaultdict(list)
    by_state = defaultdict(int)
    by_category_state = defaultdict(lambda: defaultdict(int))

    for filepath, agent_id, category in discover_all_agents(category_filter):
        state = get_current_lifecycle(filepath)
        days_stale = None

        if check_freshness:
            last_mod = git_last_modified(filepath)
            if last_mod:
                days_stale = (date.today() - last_mod).days

        entry = {
            "id": agent_id,
            "category": category,
            "state": state,
            "path": str(filepath.relative_to(REPO)),
            "days_stale": days_stale,
        }
        agents[state].append(entry)
        by_state[state] += 1
        by_category_state[category][state] += 1

    return {
        "agents": dict(agents),
        "by_state": dict(by_state),
        "by_category_state": {k: dict(v) for k, v in by_category_state.items()},
    }


def print_report(report, args):
    """Print the lifecycle dashboard."""
    total = sum(report["by_state"].values())
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}  Agent Lifecycle Dashboard{RESET}")
    print(f"  Total: {total} agents  |  {date.today()}")
    if args.category:
        print(f"  Category: {args.category}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    # State distribution
    print(f"{BOLD}Portfolio by State:{RESET}")
    for state in LIFECYCLE_STATES:
        count = report["by_state"].get(state, 0)
        pct = (count / total * 100) if total else 0
        bar = "█" * int(pct / 2)
        color = STATE_COLORS.get(state, RESET)
        print(f"  {color}{state:<12}{RESET} {count:>5} ({pct:5.1f}%)  {bar}")

    # Health indicators
    draft_pct = report["by_state"].get("draft", 0) / max(1, total) * 100
    review_pct = report["by_state"].get("review", 0) / max(1, total) * 100
    deprecated_pct = report["by_state"].get("deprecated", 0) / max(1, total) * 100

    print(f"\n{BOLD}Health Indicators:{RESET}")
    if review_pct > 20:
        print(f"  {RED}⚠ Review backlog: {review_pct:.0f}% agents awaiting review — bottleneck detected{RESET}")
    elif review_pct > 5:
        print(f"  {YELLOW}⚠ Review queue: {review_pct:.0f}% agents in review — manageable{RESET}")
    else:
        print(f"  {GREEN}✓ Review queue healthy{RESET}")

    if draft_pct > 30:
        print(f"  {YELLOW}⚠ High draft ratio: {draft_pct:.0f}% — many agents still in progress{RESET}")
    if deprecated_pct > 10:
        print(f"  {YELLOW}⚠ {deprecated_pct:.0f}% agents deprecated — consider cleanup{RESET}")

    # Stale agents (deprecated or published but not updated in 12+ months)
    stale_pub = [a for a in report["agents"].get("published", [])
                 if a.get("days_stale") and a["days_stale"] > 365]
    stale_dep = [a for a in report["agents"].get("deprecated", [])
                 if a.get("days_stale") and a["days_stale"] > 365]
    if stale_pub or stale_dep:
        print(f"\n{BOLD}Stale Agents (>12 months):{RESET}")
        for a in stale_pub[:10]:
            print(f"  {YELLOW}{a['id']}{RESET} ({a['category']}) — published, {a['days_stale']}d stale")
        for a in stale_dep[:5]:
            print(f"  {RED}{a['id']}{RESET} ({a['category']}) — deprecated, {a['days_stale']}d — candidate for removal")

    # Category breakdown
    if not args.category:
        print(f"\n{BOLD}Categories with Most Drafts/Reviews:{RESET}")
        cat_issues = []
        for cat, states in report["by_category_state"].items():
            draft_count = states.get("draft", 0)
            review_count = states.get("review", 0)
            if draft_count + review_count > 0:
                cat_issues.append((cat, draft_count, review_count,
                                   sum(states.values())))
        cat_issues.sort(key=lambda x: -(x[1] + x[2]))
        for cat, drafts, reviews, total_cat in cat_issues[:10]:
            print(f"  {cat:<28} {YELLOW}{drafts} draft{RESET}  {CYAN}{reviews} review{RESET}  ({total_cat} total)")

    # Agents in review (actionable list)
    in_review = report["agents"].get("review", [])
    if in_review and len(in_review) <= 20:
        print(f"\n{BOLD}Agents Awaiting Review ({len(in_review)}):{RESET}")
        for a in in_review:
            print(f"  {CYAN}{a['id']}{RESET} ({a['category']})")


def print_json_report(report):
    """Machine-readable JSON output."""
    json.dump({
        "generated": str(date.today()),
        "total_agents": sum(report["by_state"].values()),
        "by_state": report["by_state"],
        "by_category_state": report["by_category_state"],
    }, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def sync_lifecycle_fields(category_filter=None, dry_run=False):
    """Add lifecycle: published to all agents that don't have the field."""
    count = 0
    for filepath, agent_id, category in discover_all_agents(category_filter):
        content = filepath.read_text(encoding="utf-8")
        fm = get_frontmatter_text(content)
        current = get_field("lifecycle", fm)
        if not current:
            count += 1
            if dry_run:
                print(f"  would add: lifecycle: published → {agent_id} ({category})")
            else:
                ok, msg = set_lifecycle(filepath, "published")
                if ok:
                    print(f"  {GREEN}✓{RESET} {agent_id} ({category}): {msg}")
                else:
                    print(f"  {RED}✗{RESET} {agent_id}: {msg}")

    if dry_run:
        print(f"\n  {YELLOW}DRY RUN: {count} agents would get 'lifecycle: published'{RESET}")
    else:
        print(f"\n  {GREEN}Synced: {count} agents now have lifecycle: published{RESET}")


def find_stale_agents(months=12):
    """Find agents that haven't been modified in N months."""
    cutoff = date.today() - timedelta(days=months * 30)
    stale = []

    for filepath, agent_id, category in discover_all_agents():
        last_mod = git_last_modified(filepath)
        if last_mod and last_mod < cutoff:
            state = get_current_lifecycle(filepath)
            stale.append((agent_id, category, state, last_mod,
                         (date.today() - last_mod).days))

    stale.sort(key=lambda x: x[4], reverse=True)
    return stale


def main():
    parser = argparse.ArgumentParser(
        description="Agent lifecycle management for The Agency")
    parser.add_argument("--report", action="store_true",
                        help="Show lifecycle dashboard")
    parser.add_argument("--category", "-c",
                        help="Filter to specific category")
    parser.add_argument("--agent", "-a",
                        help="Target a specific agent (for --status or --transition)")
    parser.add_argument("--status", action="store_true",
                        help="Show current lifecycle state (requires --agent)")
    parser.add_argument("--transition",
                        help=f"Transition to new state. Valid: {', '.join(LIFECYCLE_STATES)}")
    parser.add_argument("--note",
                        help="Note/reason for the transition")
    parser.add_argument("--sync", action="store_true",
                        help="Add lifecycle: published to agents missing the field")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without making them")
    parser.add_argument("--find-stale", action="store_true",
                        help="Find agents not updated recently")
    parser.add_argument("--months", type=int, default=12,
                        help="Staleness threshold in months (default: 12)")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args()

    # --status mode
    if args.status:
        if not args.agent:
            print("ERROR: --status requires --agent <id>", file=sys.stderr)
            sys.exit(1)
        for filepath, agent_id, category in discover_all_agents():
            if agent_id == args.agent:
                state = get_current_lifecycle(filepath)
                color = STATE_COLORS.get(state, RESET)
                print(f"\n  Agent:  {BOLD}{agent_id}{RESET} ({category})")
                print(f"  State:  {color}{state}{RESET}")
                valid = VALID_TRANSITIONS.get(state, ())
                if valid:
                    print(f"  Valid transitions: {', '.join(valid)}")
                return
        print(f"ERROR: Agent '{args.agent}' not found.", file=sys.stderr)
        sys.exit(1)

    # --transition mode
    if args.transition:
        if args.transition not in LIFECYCLE_STATES:
            print(f"ERROR: Invalid state '{args.transition}'. Valid: {', '.join(LIFECYCLE_STATES)}",
                  file=sys.stderr)
            sys.exit(1)

        if args.agent:
            # Single agent transition
            for filepath, agent_id, category in discover_all_agents():
                if agent_id == args.agent:
                    ok, msg = set_lifecycle(filepath, args.transition, args.note or "")
                    color = GREEN if ok else RED
                    print(f"\n  {color}{'✓' if ok else '✗'}{RESET} {agent_id}: {msg}")
                    if not ok:
                        sys.exit(1)
                    return
            print(f"ERROR: Agent '{args.agent}' not found.", file=sys.stderr)
            sys.exit(1)

        elif args.category:
            # Batch transition by category
            count = 0
            for filepath, agent_id, category in discover_all_agents(args.category):
                current = get_current_lifecycle(filepath)
                if current == args.transition:
                    continue
                ok, msg = set_lifecycle(filepath, args.transition, args.note or "")
                status = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
                if ok:
                    count += 1
                print(f"  {status} {agent_id}: {msg}")
            print(f"\n  Transitioned {count} agents to '{args.transition}' in {args.category}")
            return

        else:
            print("ERROR: --transition requires --agent or --category", file=sys.stderr)
            sys.exit(1)

    # --sync mode
    if args.sync:
        sync_lifecycle_fields(category_filter=args.category, dry_run=args.dry_run)
        return

    # --find-stale mode
    if args.find_stale:
        stale = find_stale_agents(months=args.months)
        print(f"\n{BOLD}Agents not modified in {args.months}+ months ({len(stale)} found):{RESET}\n")
        for agent_id, category, state, last_mod, days in stale[:50]:
            color = STATE_COLORS.get(state, RESET)
            print(f"  {color}{state:<12}{RESET} {agent_id:<50} {category:<20} {last_mod} ({days}d)")
        if len(stale) > 50:
            print(f"\n  ... and {len(stale) - 50} more")
        return

    # Default: --report
    report = build_lifecycle_report(category_filter=args.category)
    if args.json:
        print_json_report(report)
    else:
        print_report(report, args)


if __name__ == "__main__":
    main()
