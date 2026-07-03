#!/usr/bin/env bash
#
# check-dupes.sh — Detect near-duplicate agents by name and description similarity.
#
# Reads AGENTS.json and uses Python difflib to compute string similarity
# ratios between all agent pairs.  Flags pairs above the similarity
# threshold as potential duplicates that merit manual review.
#
# Usage:
#   ./scripts/check-dupes.sh [--threshold 0.85] [--category <name>] [--help]
#
#   --threshold N   Similarity ratio above which to flag (default: 0.85; 0–1)
#   --category NAME  Only compare agents in this category
#   --help           Show this help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEX="$REPO_ROOT/AGENTS.json"

# --- defaults ---
THRESHOLD="0.85"
CATEGORY_FILTER=""

# --- helpers ---
usage() {
  sed -n '3,12p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
}

err() { echo "[ERR] $*" >&2; }

# --- main ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --threshold) THRESHOLD="$2"; shift 2 ;;
    --category)  CATEGORY_FILTER="$2"; shift 2 ;;
    --help|-h)   usage ;;
    *)           err "Unknown option: $1"; usage ;;
  esac
done

[[ -f "$INDEX" ]] || { err "AGENTS.json not found. Run: ./scripts/generate-index.sh"; exit 1; }

# Run duplicate detection via Python
export PYTHONIOENCODING=utf-8
python3 - "$INDEX" "$THRESHOLD" "$CATEGORY_FILTER" <<'PYEOF'
import json, sys
from difflib import SequenceMatcher

index_path  = sys.argv[1]
threshold   = float(sys.argv[2])
cat_filter  = sys.argv[3]

with open(index_path, encoding="utf-8") as f:
    data = json.load(f)

agents = data["agents"]
if cat_filter:
    agents = [a for a in agents if a["category"] == cat_filter]
    print(f"Category filter: {cat_filter} ({len(agents)} agents)\n")

n = len(agents)
pairs = []

for i in range(n):
    for j in range(i + 1, n):
        a, b = agents[i], agents[j]

        name_ratio = SequenceMatcher(None,
            a["name"].lower(), b["name"].lower()).ratio()

        desc_ratio = SequenceMatcher(None,
            a.get("description","").lower(),
            b.get("description","").lower()).ratio()

        # weighted composite: name similarity is stronger signal
        composite = name_ratio * 0.6 + desc_ratio * 0.4

        if composite >= threshold:
            pairs.append((composite, name_ratio, desc_ratio, a, b))

pairs.sort(key=lambda x: x[0], reverse=True)

if not pairs:
    print(f"No duplicate pairs found (threshold={threshold}).")
    sys.exit(0)

print(f"Potential duplicate agents (threshold={threshold}, composite≥{threshold}):\n")
for comp, nr, dr, a, b in pairs:
    print(f"  [{comp:.0%}]  {a['name']}  <->  {b['name']}")
    print(f"            name={nr:.0%}  desc={dr:.0%}")
    print(f"            {a['category']}/{a['id']}")
    print(f"            {b['category']}/{b['id']}")
    print()

print(f"Total: {len(pairs)} pair(s) flagged for review.")
sys.exit(1)
PYEOF
