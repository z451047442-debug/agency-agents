#!/usr/bin/env bash
# Search The Agency's agents by keyword, category, or list all.
# Usage: ./scripts/search-agents.sh [query] [--category name] [--list-categories] [--stats] [--page N] [--per-page N]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Resolve Python 3 interpreter (python3 on Linux/macOS, python on Windows).
PYTHON=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)" 2>/dev/null; then
      PYTHON="$candidate"
      break
    fi
  fi
done
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python 3.9+ required. Install from https://python.org." >&2
  exit 1
fi
INDEX="$SCRIPT_DIR/../AGENTS.json"
# Normalize to absolute path and convert to Windows-native path if needed (for Python)
INDEX="$(cd "$(dirname "$INDEX")" 2>/dev/null && pwd)/$(basename "$INDEX")"
if command -v cygpath &>/dev/null; then
  INDEX="$(cygpath -m "$INDEX" 2>/dev/null || echo "$INDEX")"
fi
[[ -f "$INDEX" ]] || { echo "ERROR: AGENTS.json not found. Run: ./scripts/generate-index.sh"; exit 1; }

CATEGORY=""; QUERY=""; LIST_CATS=false; STATS=false; PAGE=1; PER_PAGE=25
while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c) CATEGORY="$2"; shift 2 ;;
    --list-categories|-l) LIST_CATS=true; shift ;;
    --stats|-s) STATS=true; shift ;;
    --page) PAGE="$2"; shift 2 ;;
    --per-page) PER_PAGE="$2"; shift 2 ;;
    --help|-h) echo "Usage: search-agents.sh [query] [--category name] [--list-categories] [--stats] [--page N] [--per-page N]"; exit 0 ;;
    *) QUERY="$1"; shift ;;
  esac
done

# Stats mode
if $STATS; then
  $PYTHON -c "
import json; d=json.load(open('$INDEX',encoding='utf-8'))
from collections import Counter
cats=Counter(a['category'] for a in d['agents'])
print(f'Categories: {len(cats)} | Agents: {d[\"total_agents\"]} | Generated: {d[\"generated\"]}')
print('Top 10:'); [print(f'  {c:24s} {n}') for c,n in cats.most_common(10)]
"
  exit 0
fi

# List categories mode
if $LIST_CATS; then
  $PYTHON -c "
import json; d=json.load(open('$INDEX',encoding='utf-8'))
from collections import Counter
cats=Counter(a['category'] for a in d['agents'])
print(f'\n{d[\"total_categories\"]} categories, {d[\"total_agents\"]} agents\n')
for c,n in cats.most_common():
    print(f'  {c:26s} {n:4d}')
print()
"
  exit 0
fi

# Search mode
$PYTHON -c "
import json, sys, re
d=json.load(open('$INDEX',encoding='utf-8'))
results=[]
query='${QUERY}'.lower()
cat='${CATEGORY}'.lower()
for a in d['agents']:
    if cat and a['category'].lower() != cat: continue
    if query:
        haystack=(a.get('name','')+' '+a.get('description','')+' '+a['id']).lower()
        # fuzzy: split query into words, all must match
        words=query.split()
        if not all(w in haystack for w in words): continue
    results.append(a)
if not results:
    print(f'\nNo agents found: {query or cat}')
    print('Try: ./scripts/search-agents.sh --list-categories\n')
    sys.exit(0)
if query and cat:
    print(f'\n{q} in {cat}/ {len(results)} agent(s)')
elif query:
    print(f'\n{q} {len(results)} agent(s)')
else:
    print(f'\n{cat}/ {len(results)} agent(s)')
print()
	page=int('${PAGE}'); per_page=int('${PER_PAGE}')
	per_page=max(1, min(per_page, 100))
	total_pages=(len(results)+per_page-1)//per_page
	page=max(1, min(page, total_pages)) if total_pages>0 else 1
	start=(page-1)*per_page; end=start+per_page
	paginated=results[start:end]
	if total_pages>1:
	    print(f'  Page {page}/{total_pages} ({len(results)} total, showing {start+1}-{min(end,len(results))})')
print(f'{\"EMOJI\":6s} {\"AGENT\":30s} {\"CATEGORY\":24s} {\"DESCRIPTION\"}')
print(f'{\"-\"*6:6s} {\"-\"*30:30s} {\"-\"*24:24s} {\"-\"*60}')
	for a in paginated:
	    print(f'{a.get(\"emoji\",\"\"):6s} {a[\"name\"][:29]:30s} {a[\"category\"]:24s} {a.get(\"description\",\"\")[:60]}')
	if total_pages>1 and page<total_pages:
	    print(f'  Next: --page {page+1}')
print()
"
