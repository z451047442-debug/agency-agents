#!/usr/bin/env python
"""Validate AGENTS.json — JSON syntax, schema conformance, and filesystem cross-reference.

Usage:
    python scripts/validate-index.py [--schema-only] [--sync-only] [--path <index.json>]

Exit codes:
    0   All checks passed.
    1   Validation failed (syntax, schema, or cross-reference mismatch).
    2   Usage error (file not found, etc.).

Requires: jsonschema (pip install jsonschema). If not installed, only JSON syntax
and filesystem cross-reference checks run; schema validation is skipped with a warning.
"""

import json
import os
import sys
from pathlib import Path

from _shared import EXCLUDE_DIRS, REPO

DEFAULT_INDEX = REPO / "AGENTS.json"
SCHEMA_FILE = REPO / "schemas" / "agent-index.schema.json"


def load_json(path):
    """Load a JSON file, returning (data, error_message)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON: {e}"
    except FileNotFoundError:
        return None, f"File not found: {path}"
    except OSError as e:
        return None, f"Error reading {path}: {e}"


def load_schema(path):
    """Load a JSON schema, returning (schema, error_message)."""
    return load_json(path)


def validate_schema(data, schema):
    """Validate data against a JSON Schema. Returns list of error strings."""
    try:
        import jsonschema
    except ImportError:
        return ["SKIP: jsonschema package not installed; "
                "run 'pip install jsonschema' for schema validation"]

    validator = jsonschema.Draft7Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(data), key=lambda e: str(e.path)):
        path_str = " -> ".join(str(p) for p in err.path) if err.path else "(root)"
        errors.append(f"  {path_str}: {err.message}")
    return errors


def discover_md_files(repo_root):
    """Find all .md files in agent category directories.

    Returns a dict mapping relative Unix-style path -> absolute Path.
    Mirror's _discover_dirs.sh logic: scan every repo-level directory,
    excluding known non-agent dirs. Recursively walks each category
    to pick up subdirectory agents (e.g. game-development/blender/).
    """
    result = {}
    for entry in sorted(os.listdir(repo_root)):
        entry_path = os.path.join(repo_root, entry)
        if not os.path.isdir(entry_path) or entry.startswith("."):
            continue
        if entry in EXCLUDE_DIRS:
            continue
        for root, _dirs, files in os.walk(entry_path):
            for fn in files:
                if fn.endswith(".md"):
                    abs_path = os.path.join(root, fn)
                    rel = os.path.relpath(abs_path, repo_root).replace(os.sep, "/")
                    result[rel] = abs_path
    return result


def check_cross_reference(data, md_files):
    """Cross-reference AGENTS.json entries against filesystem .md files.

    Returns (has_errors, orphan_paths, missing_paths, message_lines).
    """
    has_errors = False
    lines = []

    agent_paths = {a["path"] for a in data.get("agents", [])}

    orphan = agent_paths - set(md_files.keys())
    missing = set(md_files.keys()) - agent_paths

    if orphan:
        has_errors = True
        lines.append("ERROR: Orphan entries in AGENTS.json (referenced path not on disk):")
        for p in sorted(orphan):
            lines.append(f"  {p}")
    else:
        lines.append("OK: No orphan entries (every AGENTS.json path exists on disk).")

    if missing:
        has_errors = True
        lines.append("ERROR: .md files on disk not listed in AGENTS.json:")
        for p in sorted(missing):
            lines.append(f"  {p}")
    else:
        lines.append("OK: No missing entries (every .md file is in AGENTS.json).")

    # Integrity: agent count should match
    json_count = len(data.get("agents", []))
    if json_count != data.get("total_agents"):
        has_errors = True
        lines.append(f"ERROR: total_agents field ({data.get('total_agents')}) "
                     f"does not match actual agent count ({json_count}).")
    else:
        lines.append(f"OK: total_agents ({json_count}) matches agent array length.")

    return has_errors, orphan, missing, lines


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Validate AGENTS.json")
    parser.add_argument("--path", default=str(DEFAULT_INDEX),
                        help="Path to AGENTS.json (default: repo-root/AGENTS.json)")
    parser.add_argument("--schema-only", action="store_true",
                        help="Only validate JSON syntax and schema (skip filesystem cross-check)")
    parser.add_argument("--sync-only", action="store_true",
                        help="Only cross-check AGENTS.json against filesystem .md files")
    args = parser.parse_args()

    index_path = Path(args.path)
    errors = 0
    checks = 0

    # ---- 1. JSON syntax -------------------------------------------------------
    print("=== AGENTS.json Validation ===\n")
    print(f"Index file: {index_path}")
    data, err = load_json(index_path)
    if err:
        print(f"FAIL: {err}")
        sys.exit(1)
    print("PASS: Valid JSON syntax.")
    checks += 1

    # ---- 2. Schema validation -------------------------------------------------
    if not args.sync_only:
        schema, schema_err = load_schema(SCHEMA_FILE)
        if schema_err:
            print(f"FAIL: Could not load schema: {schema_err}")
            errors += 1
        else:
            schema_errors = validate_schema(data, schema)
            if any(e.startswith("SKIP:") for e in schema_errors):
                print(f"WARN: {schema_errors[0]}")
            elif schema_errors:
                print(f"FAIL: Schema validation found {len(schema_errors)} error(s):")
                for e in schema_errors:
                    print(e)
                errors += 1
            else:
                print("PASS: Schema validation passed.")
            checks += 1

    # ---- 3. Duplicate IDs -----------------------------------------------------
    if not args.sync_only:
        agents = data.get("agents", [])
        ids = [a["id"] for a in agents]
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        if dupes:
            print(f"FAIL: Duplicate agent IDs found: {', '.join(dupes)}")
            errors += 1
        else:
            print(f"PASS: No duplicate IDs in AGENTS.json ({len(agents)} agents).")
        checks += 1

    # ---- 4. Filesystem cross-reference ----------------------------------------
    if not args.schema_only:
        md_files = discover_md_files(REPO)
        has_err, orphan, missing, lines = check_cross_reference(data, md_files)
        for line in lines:
            print(line)
        if has_err:
            errors += 1
        checks += 1

    # ---- Summary --------------------------------------------------------------
    print()
    if errors:
        print(f"FAIL: {errors} check(s) failed out of {checks} total.")
        sys.exit(1)
    else:
        print(f"PASS: All {checks} checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
