#!/usr/bin/env python3
"""Run all quality checks in a single process for performance.

Previously used subprocess.run() for every step, which re-discovered 1,414
agents and re-imported shared modules for each of the first 3 steps. Now runs
lint, deps, and scoring in-process while keeping ruff and pytest as subprocesses.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent


def _run_script(module_name, filepath, args=None):
    """Load and run a Python script's main() in-process. Returns True on success."""
    if args is None:
        args = []
    old_argv = sys.argv
    sys.argv = [str(filepath)] + args
    try:
        spec = importlib.util.spec_from_file_location(module_name, str(filepath))
        if spec is None or spec.loader is None:
            print(f"ERROR: Cannot load module {module_name} from {filepath}", file=sys.stderr)
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
        return True
    except SystemExit as e:
        return e.code in (0, None)
    except Exception as e:
        print(f"ERROR: {module_name} failed: {e}", file=sys.stderr)
        return False
    finally:
        sys.argv = old_argv


def main():
    steps = [
        ("Agent Lint", "lint_agents", SCRIPT_DIR / "lint-agents.py",
         ["--all", "--no-freshness"]),
        ("Dependencies", "analyze_deps", SCRIPT_DIR / "analyze-deps.py",
         ["--validate"]),
        ("Quality Score", "score_agents", SCRIPT_DIR / "score-agents.py", []),
    ]

    passed = 0
    failed = 0

    print("=== Agency Quality Pipeline ===")

    for i, (label, mod_name, path, args) in enumerate(steps, 1):
        print(f"\n[{i}/{len(steps) + 2}] {label}")
        print("-" * 40)
        ok = _run_script(mod_name, path, args)
        if ok:
            passed += 1
        else:
            failed += 1

    external_steps = [
        ("Security Audit", [sys.executable, str(SCRIPT_DIR / "audit-security.py"), "--check"]),
        ("Python Lint (Ruff)", [sys.executable, "-m", "ruff", "check", str(SCRIPT_DIR)]),
        # Relaxed threshold (35%) for the quality pipeline's own quick run.
        # The CI job enforces 80% via pyproject.toml [tool.coverage.report] fail_under.
        ("Tests + Coverage", [
            sys.executable, "-m", "pytest", str(ROOT / "tests"),
            "-q", "--cov=scripts", "--cov-fail-under=35",
        ]),
    ]

    for i, (label, cmd) in enumerate(external_steps, len(steps) + 1):
        print(f"\n[{i}/{len(steps) + len(external_steps)}] {label}")
        print("-" * 40)
        result = subprocess.run(cmd, cwd=str(ROOT))
        if result.returncode == 0:
            passed += 1
        else:
            failed += 1

    print(f"\n=== Pipeline: {passed} passed, {failed} failed ===")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
