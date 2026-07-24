#!/usr/bin/env python
"""Lightweight opt-in usage telemetry for The Agency.

All data stays local — no network calls, no third-party services.
Opt-in only. Users are prompted once on first script run.

Usage:
    python scripts/telemetry.py --status           check if enabled
    python scripts/telemetry.py --enable            opt in
    python scripts/telemetry.py --disable           opt out
    python scripts/telemetry.py --record <action> --agent <id>   record event
    python scripts/telemetry.py --report            view collected data
    python scripts/telemetry.py --recommend         get improvement suggestions
"""

import argparse
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

UTC = timezone.utc

TELEMETRY_DIR = Path.home() / ".agency"
TELEMETRY_FILE = TELEMETRY_DIR / "telemetry.json"
MAX_EVENTS = 5000


def _load():
    if not TELEMETRY_FILE.exists():
        return {"enabled": False, "events": [], "metadata": {}}
    try:
        return json.loads(TELEMETRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"enabled": False, "events": [], "metadata": {}}


def _save(data):
    TELEMETRY_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TELEMETRY_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(TELEMETRY_FILE)


def is_enabled():
    return _load().get("enabled", False)


def enable():
    data = _load()
    data["enabled"] = True
    data["metadata"]["opt_in_at"] = datetime.now(UTC).isoformat()
    data["metadata"]["os"] = platform.system()
    data["metadata"]["python"] = platform.python_version()
    _save(data)
    print("Telemetry enabled. All data stored locally: ~/.agency/telemetry.json")
    print("No network calls. Run --report to view, --disable to opt out.")


def disable():
    data = _load()
    data["enabled"] = False
    _save(data)
    print("Telemetry disabled.")


def record_event(action, **kwargs):
    if not is_enabled():
        return
    data = _load()
    event = {"timestamp": datetime.now(UTC).isoformat(), "action": action}
    event.update({k: v for k, v in kwargs.items() if v is not None})
    data["events"].append(event)
    if len(data["events"]) > MAX_EVENTS:
        data["events"] = data["events"][-MAX_EVENTS:]
    _save(data)


def print_report():
    data = _load()
    if not data.get("enabled"):
        print("Telemetry not enabled. Run --enable to opt in.", file=sys.stderr)
        sys.exit(1)
    events = data.get("events", [])
    if not events:
        print("No events yet. Run some agency scripts first.")
        return
    actions = Counter(e["action"] for e in events)
    agents = Counter(e["agent"] for e in events if "agent" in e)
    tools = Counter(e["tool"] for e in events if "tool" in e)
    categories = Counter(e["category"] for e in events if "category" in e)

    print(f"\n{'='*55}\nTelemetry Report — {len(events)} events\n{'='*55}\n")
    print("Script Usage:")
    for action, count in actions.most_common(10):
        print(f"  {action:<30} {count:>4}")

    if agents:
        print(f"\nTop Agents ({len(agents)} unique):")
        for agent, count in agents.most_common(10):
            print(f"  {agent:<40} {count:>3}")

    if tools:
        print(f"\nTools ({len(tools)} unique):")
        for tool, count in tools.most_common(5):
            print(f"  {tool:<20} {count:>3}")

    if categories:
        print(f"\nCategories ({len(categories)} unique):")
        for cat, count in categories.most_common(10):
            print(f"  {cat:<30} {count:>3}")

    meta = data.get("metadata", {})
    if meta:
        print(f"\nEnvironment: OS={meta.get('os','?')} Python={meta.get('python','?')}")
        if "opt_in_at" in meta:
            print(f"  Opt-in: {meta['opt_in_at'][:10]}")


def print_recommendations():
    data = _load()
    events = data.get("events", [])
    if not events:
        print("No usage data yet.")
        return

    searches = [e["term"] for e in events if e["action"] == "search" and "term" in e]
    installed = Counter(e["agent"] for e in events if e["action"] == "install" and "agent" in e)
    actions = Counter(e["action"] for e in events)

    print(f"\n{'='*55}\nImprovement Recommendations\n{'='*55}\n")
    suggestions = []

    if installed:
        REPO_ROOT = Path(__file__).resolve().parent.parent
        import subprocess as sp
        for agent, count in installed.most_common(10):
            found = list(REPO_ROOT.glob(f"**/{agent}.md"))
            if found:
                r = sp.run(
                    [sys.executable, str(REPO_ROOT/"scripts"/"score-agents.py"),
                     "--file", str(found[0]), "--no-freshness", "--json"],
                    capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT))
                if r.returncode == 0:
                    try:
                        sd = json.loads(r.stdout)
                        ag = sd.get("agents", [{}])[0]
                        if ag.get("total", 0) < 7:
                            suggestions.append(
                                f"  PRIORITY: {agent} (installed {count}x) scores "
                                f"{ag['total']}/10 ({ag.get('grade','?')}). "
                                f"Popular but needs depth enhancement."
                            )
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

    if searches:
        for term, count in Counter(searches).most_common(5):
            suggestions.append(
                f"  INSIGHT: '{term}' searched {count}x — consider adding related agents."
            )

    total = sum(actions.values()) if actions else 0
    if total > 10:
        lint_pct = actions.get("lint", 0) / total * 100
        score_pct = actions.get("score", 0) / total * 100
        if lint_pct > 50:
            suggestions.append(f"  PATTERN: lint={lint_pct:.0f}% of usage. Add auto-fix hints to lint output.")
        if score_pct < 5:
            suggestions.append(f"  PATTERN: score={score_pct:.0f}% of usage. Surface 'score' in install output.")

    if not suggestions:
        suggestions.append("  Not enough data yet — keep using the tools.")
    for s in suggestions:
        print(s)
    print()


def main():
    parser = argparse.ArgumentParser(description="The Agency telemetry (opt-in, local-only)")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--enable", action="store_true")
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--record")
    parser.add_argument("--agent")
    parser.add_argument("--tool")
    parser.add_argument("--category")
    parser.add_argument("--term")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--recommend", action="store_true")
    args = parser.parse_args()

    if args.status:
        print(f"Telemetry: {'enabled' if is_enabled() else 'disabled'}")
        print(f"Data: {TELEMETRY_FILE}")
    elif args.enable:
        enable()
    elif args.disable:
        disable()
    elif args.record:
        record_event(args.record, agent=args.agent, tool=args.tool,
                     category=args.category, term=args.term)
    elif args.report:
        print_report()
    elif args.recommend:
        print_recommendations()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
