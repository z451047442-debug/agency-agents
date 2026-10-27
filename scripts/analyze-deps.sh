#!/usr/bin/env bash
#
# analyze-deps.sh — Scan agent bodies for cross-references and build a dependency graph.
#
# Reads each agent's body content and extracts references to other agents
# (by ID pattern: category-slug). Outputs a JSON dependency graph.
#
# Usage:
#   ./scripts/analyze-deps.sh [--category name] [--output path] [--mermaid]
#
#   --category name   Only analyze one category
#   --output path     Write JSON to path (default: docs/depends-network.json)
#   --mermaid         Also output a Mermaid graph to stdout

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT="$REPO_ROOT/docs/depends-network.json"
CATEGORY_FILTER=""
MERMAID=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c) CATEGORY_FILTER="${2:?'--category requires a value'}"; shift 2 ;;
    --output|-o)   OUTPUT="${2:?'--output requires a value'}"; shift 2 ;;
    --mermaid)     MERMAID=true; shift ;;
    --help|-h)
      echo "Usage: analyze-deps.sh [--category name] [--output path] [--mermaid]"
      echo "Builds an agent dependency graph from body content cross-references."
      exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

# Export the resolved values for the embedded Python program. Without this the
# Python side silently falls back to defaults and --output can truncate a file
# while writing the result somewhere else.
export REPO_ROOT OUTPUT CATEGORY_FILTER MERMAID
cd "$REPO_ROOT"

PYBIN="${PYTHON:-}"
if [[ -z "$PYBIN" ]]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      PYBIN="$candidate"
      break
    fi
  done
fi
if [[ -z "$PYBIN" ]]; then
  echo "ERROR: Python 3 is required to analyze dependencies." >&2
  exit 1
fi

"$PYBIN" <<'PYEOF'
import json
import os
import re
import sys
import tempfile

repo = os.environ.get("REPO_ROOT", ".")
output = os.environ.get("OUTPUT", "docs/depends-network.json")
category_filter = os.environ.get("CATEGORY_FILTER", "").strip()
show_mermaid = os.environ.get("MERMAID", "false") == "true"

# Agent ID pattern: lowercase-kebab-case with category prefix
agent_id_pat = re.compile(r"[a-z][a-z0-9]*-[a-z][a-z0-9-]*")

with open(os.path.join(repo, "AGENTS.json"), encoding="utf-8") as fh:
    index = json.load(fh)

known_ids = {a["id"] for a in index["agents"]}
agents = index["agents"]
if category_filter:
    agents = [a for a in agents if a["category"] == category_filter]
    if not agents:
        print(f"No agents found in category '{category_filter}'", file=sys.stderr)
        sys.exit(2)

nodes = []
edges = []
edge_set = set()

for agent in agents:
    filepath = os.path.join(repo, agent["path"])
    if not os.path.exists(filepath):
        continue

    with open(filepath, encoding="utf-8") as fh:
        content = fh.read()

    # Extract body (after second ---)
    parts = content.split("---", 2)
    body = parts[2] if len(parts) > 2 else ""

    # Find all agent ID references in the body
    refs = set()
    for match in agent_id_pat.finditer(body):
        aid = match.group()
        if aid in known_ids and aid != agent["id"]:
            refs.add(aid)

    nodes.append({"id": agent["id"], "category": agent["category"], "name": agent["name"]})

    for ref in refs:
        edge_key = (agent["id"], ref)
        if edge_key not in edge_set:
            edge_set.add(edge_key)
            edges.append({"from": agent["id"], "to": ref})

out_path = os.path.abspath(output)
if os.path.isdir(out_path):
    print(f"ERROR: output path is a directory: {out_path}", file=sys.stderr)
    sys.exit(2)
parent = os.path.dirname(out_path) or "."
os.makedirs(parent, exist_ok=True)

# Write atomically so a failure cannot leave the previous graph truncated.
fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".depends-", suffix=".json")
try:
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"nodes": nodes, "edges": edges}, fh, indent=2)
    os.replace(tmp_path, out_path)
except Exception:
    try:
        os.unlink(tmp_path)
    except OSError:
        pass
    raise

print(f"Graph: {len(nodes)} nodes, {len(edges)} edges -> {out_path}")

# Top referenced agents
from collections import Counter

ref_counts = Counter(edge["to"] for edge in edges)
print("\nTop 10 most-referenced agents:")
for aid, count in ref_counts.most_common(10):
    name = next((node["name"] for node in nodes if node["id"] == aid), aid)
    print(f"  {count:3d}  {name} ({aid})")

# Orphan agents (no references to/from)
referenced = {edge["to"] for edge in edges} | {edge["from"] for edge in edges}
orphans = [node for node in nodes if node["id"] not in referenced]
if orphans:
    print(f"\n{len(orphans)} orphan agents (no cross-references):")
    for node in orphans[:10]:
        print(f"  {node['name']} ({node['id']})")
    if len(orphans) > 10:
        print(f"  ... and {len(orphans) - 10} more")

# Mermaid output
if show_mermaid:
    print("\n```mermaid")
    print("graph TD")
    for edge in edges:
        print(f'  {edge["from"]}[{edge["from"]}] --> {edge["to"]}[{edge["to"]}]')
    print("```")
PYEOF
