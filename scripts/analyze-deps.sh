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
    --category|-c) CATEGORY_FILTER="$2"; shift 2 ;;
    --output|-o)   OUTPUT="$2"; shift 2 ;;
    --mermaid)     MERMAID=true; shift ;;
    --help|-h)
      echo "Usage: analyze-deps.sh [--category name] [--output path] [--mermaid]"
      echo "Builds an agent dependency graph from body content cross-references."
      exit 0 ;;
    *) shift ;;
  esac
done

# Collect files
source "$SCRIPT_DIR/_discover_dirs.sh"
AGENT_DIRS=()
while IFS= read -r d; do AGENT_DIRS+=("$d"); done < <(discover_agent_dirs)

# Build the graph: extract [[agent-id]] references and inline agent-id mentions
TMPFILE=$(mktemp)
trap 'rm -f "$TMPFILE"' EXIT

echo '{"nodes":[],"edges":[]}' > "$OUTPUT"

python3 << 'PYEOF'
import json, os, re, sys

repo = os.environ.get('REPO_ROOT', '.')
output = os.environ.get('OUTPUT', 'docs/depends-network.json')

# Agent ID pattern: lowercase-kebab-case with category prefix
agent_id_pat = re.compile(r'[a-z][a-z0-9]*-[a-z][a-z0-9-]*')

# Build a set of all known agent IDs from AGENTS.json
with open(os.path.join(repo, 'AGENTS.json'), encoding='utf-8') as f:
    index = json.load(f)
known_ids = {a['id'] for a in index['agents']}

# Read all agent files
nodes = []
edges = []
edge_set = set()

for agent in index['agents']:
    filepath = os.path.join(repo, agent['path'])
    if not os.path.exists(filepath):
        continue
    
    with open(filepath, encoding='utf-8') as f:
        content = f.read()
    
    # Extract body (after second ---)
    parts = content.split('---', 2)
    body = parts[2] if len(parts) > 2 else ''
    
    # Find all agent ID references in the body
    refs = set()
    for m in agent_id_pat.finditer(body):
        aid = m.group()
        if aid in known_ids and aid != agent['id']:
            refs.add(aid)
    
    nodes.append({'id': agent['id'], 'category': agent['category'], 'name': agent['name']})
    
    for ref in refs:
        edge_key = (agent['id'], ref)
        if edge_key not in edge_set:
            edge_set.add(edge_key)
            edges.append({'from': agent['id'], 'to': ref})

output_data = {'nodes': nodes, 'edges': edges}
with open(output, 'w', encoding='utf-8') as f:
    json.dump(output_data, f, indent=2)

print(f'Graph: {len(nodes)} nodes, {len(edges)} edges → {output}')

# Top referenced agents
from collections import Counter
ref_counts = Counter(e['to'] for e in edges)
print('\nTop 10 most-referenced agents:')
for aid, count in ref_counts.most_common(10):
    name = next((n['name'] for n in nodes if n['id'] == aid), aid)
    print(f'  {count:3d}  {name} ({aid})')

# Orphan agents (no references to/from)
referenced = set(e['to'] for e in edges) | set(e['from'] for e in edges)
orphans = [n for n in nodes if n['id'] not in referenced]
if orphans:
    print(f'\n{len(orphans)} orphan agents (no cross-references):')
    for n in orphans[:10]:
        print(f'  {n["name"]} ({n["id"]})')
    if len(orphans) > 10:
        print(f'  ... and {len(orphans) - 10} more')

# Mermaid output
if os.environ.get('MERMAID') == 'true':
    print('\n```mermaid')
    print('graph TD')
    for e in edges:
        print(f'  {e["from"]}[{e["from"]}] --> {e["to"]}[{e["to"]}]')
    print('```')
PYEOF
