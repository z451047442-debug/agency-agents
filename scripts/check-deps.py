#!/usr/bin/env python3
"""Validate depends_on references in agent frontmatter.

Thin wrapper around analyze-deps.py for cross-platform use.
Usage:
    python scripts/check-deps.py             # validate all agents
    python scripts/check-deps.py --manifest  # output depends_on.json
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYZE_SCRIPT = SCRIPT_DIR / "analyze-deps.py"

args = [sys.executable, str(ANALYZE_SCRIPT), "--validate"]
if "--manifest" in sys.argv:
    args.append("--json")

sys.exit(subprocess.run(args).returncode)
