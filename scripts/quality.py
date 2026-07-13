#!/usr/bin/env python3
"""Run all quality checks: lint, deps, score, ruff, tests.

Usage: python scripts/quality.py [--quick]
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent

steps = [
    ("Agent Lint", [sys.executable, str(SCRIPT_DIR / "lint-agents.py"), "--all", "--no-freshness"]),
    ("Dependencies", [sys.executable, str(SCRIPT_DIR / "analyze-deps.py"), "--validate"]),
    ("Quality Score", [sys.executable, str(SCRIPT_DIR / "score-agents.py")]),
    ("Python Lint (Ruff)", [sys.executable, "-m", "ruff", "check", str(SCRIPT_DIR)]),
    ("Tests + Coverage", [sys.executable, "-m", "pytest", str(ROOT / "tests"), "-q",
                          "--cov=scripts", "--cov-fail-under=35"]),
]

passed = 0
failed = 0

print("=== Agency Quality Pipeline ===")

for i, (label, cmd) in enumerate(steps, 1):
    print(f"\n[{i}/{len(steps)}] {label}")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode == 0:
        passed += 1
    else:
        failed += 1

print(f"\n=== Pipeline: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
