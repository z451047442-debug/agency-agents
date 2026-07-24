#!/usr/bin/env python
"""CLI entry point for pip-installed agency-toolkit.

Thin dispatcher that sets up the import path so scripts/ modules
can find _shared without breaking existing usage patterns.
"""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent / "scripts"

COMMANDS = {
    "lint":        ("lint-agents",         "main"),
    "score":       ("score-agents",        "main"),
    "search":      ("search-agents",       "main"),
    "convert":     ("convert",             "main"),
    "index":       ("generate-index",      "main"),
    "validate":    ("validate-index",      "main"),
    "deps":        ("analyze-deps",        "main"),
    "lifecycle":   ("agent-lifecycle",     "main"),
    "quality":     ("quality",             "main"),
    "orchestrate": ("nexus-orchestrator",  "main"),
    "ab-test":     ("ab-test",             "main"),
    "ab-evaluate": ("ab-evaluate",         "main"),
    "telemetry":   ("telemetry",           "main"),
    "feedback":    ("feedback",            "main"),
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("agency — The Agency CLI Toolkit")
        print(f"\nUsage: agency <command> [args...]\n")
        print("Commands:")
        for name, (mod, _) in sorted(COMMANDS.items()):
            print(f"  {name:<14}  scripts/{mod}.py")
        print(f"\nExample: agency search kubernetes")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print(f"Available: {', '.join(sorted(COMMANDS))}", file=sys.stderr)
        sys.exit(1)

    # Add scripts/ to path so 'from _shared import ...' works
    if str(SCRIPTS) not in sys.path:
        sys.path.insert(0, str(SCRIPTS))

    mod_name, func_name = COMMANDS[cmd]
    import importlib
    mod = importlib.import_module(mod_name)
    func = getattr(mod, func_name)

    # Replace argv so the sub-command's argparse sees its own args
    sys.argv = [f"agency-{cmd}"] + sys.argv[2:]
    func()


if __name__ == "__main__":
    main()
