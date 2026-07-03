#!/usr/bin/env bash
#
# Agent quality scoring — reads AGENTS.json, scores every agent on depth and completeness.
#
# Scoring criteria:
#   Word count:   >600 = 3pts, >300 = 2pts, >100 = 1pt, <100 = 0pt
#   Sections:     all 6 = 3pts, 4-5 = 2pts, 2-3 = 1pt, <2 = 0pt
#   Frontmatter:  has description+vibe+emoji+color: all 4 = 2pts, 3 = 1pt
#   File size:    2-8KB = 2pts, 1-10KB = 1pt
#
# Total: 0-10, Grade: A (8-10), B (5-7), C (3-4), D (0-2)
#
# Usage:
#   ./scripts/score-agents.sh              # all agents
#   ./scripts/score-agents.sh --category engineering  # one category

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEX="$REPO_ROOT/AGENTS.json"

if [[ ! -f "$INDEX" ]]; then
  echo "ERROR: AGENTS.json not found at $INDEX"
  echo "Run: ./scripts/generate-index.sh"
  exit 1
fi

# Resolve path for native Python on Windows (Git Bash / MSYS2)
resolve_py_path() {
  if command -v cygpath &>/dev/null; then
    cygpath -m "$1"
  else
    echo "$1"
  fi
}
INDEX_PY=$(resolve_py_path "$INDEX")
REPO_ROOT_PY=$(resolve_py_path "$REPO_ROOT")

CATEGORY_FILTER=""
SINGLE_FILE=""
THRESHOLD=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c) CATEGORY_FILTER="$2"; shift 2 ;;
    --file|-f)     SINGLE_FILE="$2"; shift 2 ;;
    --threshold)   THRESHOLD="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: score-agents.sh [--category name] [--file path] [--threshold N]"
      echo "Scores every agent on quality (0-10 scale) and prints a report."
      echo "  --threshold N   Exit 1 if any scored agent falls below N (for CI)"
      echo "  --file path     Score a single agent file directly"
      exit 0
      ;;
    *) shift ;;
  esac
done

echo "=== Agent Quality Report ==="

# Read agent count and generated date, also list of categories
read -r TOTAL GENERATED < <(python3 -c "
import json
d = json.load(open('$INDEX_PY', encoding='utf-8'))
print(d['total_agents'], d['generated'])
" 2>/dev/null || echo "0 unknown")

echo "Total: ${TOTAL} agents | Generated: ${GENERATED:-unknown}"
echo ""

# --file mode: score a single file directly (bypass AGENTS.json)
if [[ -n "$SINGLE_FILE" ]]; then
  if [[ ! -f "$SINGLE_FILE" ]]; then
    echo "ERROR: file not found: $SINGLE_FILE"
    exit 1
  fi
  # Derive agent info from the file path
  agent_id=$(basename "$SINGLE_FILE" .md)
  agent_category=$(basename "$(dirname "$SINGLE_FILE")")
  # Write a single entry to the agent list so the existing scoring loop processes it
  echo "${agent_id}|${agent_category}|${SINGLE_FILE#$REPO_ROOT/}" > "$AGENT_LIST_FILE"
fi

# Score every agent using python3 for JSON reading + category/agent listing
SCORES_FILE=$(mktemp)
AGENT_LIST_FILE=$(mktemp)
trap 'rm -f "$SCORES_FILE" "$AGENT_LIST_FILE" "${AGENT_LIST_FILE}.lf" "${SCORES_FILE}.cats"' EXIT

# Write agent list to temp file (avoids pipeline subshell issues)
if [[ -z "$SINGLE_FILE" ]]; then
python3 -c "
import json
d = json.load(open('$INDEX_PY', encoding='utf-8'))
agents = d['agents']
filter_val = '$CATEGORY_FILTER'
if filter_val:
    agents = [a for a in agents if a['category'] == filter_val]
for a in agents:
    print(a['id'], a['category'], a['path'], sep='|')
" > "$AGENT_LIST_FILE"
fi  # --file skip

# Normalize line endings (Windows Python produces CRLF)
tr -d '\r' < "$AGENT_LIST_FILE" > "${AGENT_LIST_FILE}.lf" && mv "${AGENT_LIST_FILE}.lf" "$AGENT_LIST_FILE"

# Score each agent by reading the list file
while IFS='|' read -r agent_id agent_category agent_path; do
  file_path="$REPO_ROOT/$agent_path"

  if [[ ! -f "$file_path" ]]; then
    echo "SKIP|${agent_id}|file not found" >> "$SCORES_FILE"
    continue
  fi

  # ---- Word count ----
  # Extract body (after second ---)
  body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$file_path")
  word_count=$(echo "$body" | wc -w | awk '{print $1}')
  word_count="${word_count:-0}"

  if [[ "$word_count" -gt 600 ]]; then
    wc_score=3
  elif [[ "$word_count" -gt 300 ]]; then
    wc_score=2
  elif [[ "$word_count" -gt 100 ]]; then
    wc_score=1
  else
    wc_score=0
  fi

  # ---- Section completeness ----
  # Check for: Identity, Mission, Rules, Deliverable, Workflow, Success Metrics
  sections_found=0
  if echo "$body" | grep -qiE '(Identity|🧠.*Identity|Your Identity)'; then
    sections_found=$((sections_found + 1))
  fi
  if echo "$body" | grep -qiE '(Core Mission|🎯.*Mission|Your Core Mission)'; then
    sections_found=$((sections_found + 1))
  fi
  if echo "$body" | grep -qiE '(Critical Rules|🚨.*Rules|Rules You Must Follow)'; then
    sections_found=$((sections_found + 1))
  fi
  if echo "$body" | grep -qi 'Deliverable'; then
    sections_found=$((sections_found + 1))
  fi
  if echo "$body" | grep -qi 'Workflow'; then
    sections_found=$((sections_found + 1))
  fi
  if echo "$body" | grep -qi 'Success Metrics'; then
    sections_found=$((sections_found + 1))
  fi

  if [[ "$sections_found" -ge 6 ]]; then
    sec_score=3
  elif [[ "$sections_found" -ge 4 ]]; then
    sec_score=2
  elif [[ "$sections_found" -ge 2 ]]; then
    sec_score=1
  else
    sec_score=0
  fi

  # ---- Frontmatter richness ----
  # Extract frontmatter (between first and second ---)
  frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file_path")
  fm_rich=0
  if echo "$frontmatter" | grep -qE '^description:'; then
    fm_rich=$((fm_rich + 1))
  fi
  if echo "$frontmatter" | grep -qE '^vibe:'; then
    fm_rich=$((fm_rich + 1))
  fi
  if echo "$frontmatter" | grep -qE '^emoji:'; then
    fm_rich=$((fm_rich + 1))
  fi
  if echo "$frontmatter" | grep -qE '^color:'; then
    fm_rich=$((fm_rich + 1))
  fi

  if [[ "$fm_rich" -ge 4 ]]; then
    fm_score=2
  elif [[ "$fm_rich" -ge 3 ]]; then
    fm_score=1
  else
    fm_score=0
  fi

  # ---- File size health ----
  file_size=$(stat -c%s "$file_path" 2>/dev/null || stat -f%z "$file_path" 2>/dev/null || echo 0)
  file_size_kb=$(( file_size / 1024 ))

  if [[ "$file_size_kb" -ge 2 && "$file_size_kb" -le 8 ]]; then
    fs_score=2
  elif [[ "$file_size_kb" -ge 1 && "$file_size_kb" -le 10 ]]; then
    fs_score=1
  else
    fs_score=0
  fi

  # ---- Total & Grade ----
  total_score=$(( wc_score + sec_score + fm_score + fs_score ))
  if [[ "$total_score" -ge 8 ]]; then
    grade="A"
  elif [[ "$total_score" -ge 5 ]]; then
    grade="B"
  elif [[ "$total_score" -ge 3 ]]; then
    grade="C"
  else
    grade="D"
  fi

  echo "${total_score}|${grade}|${agent_id}|${agent_category}|${word_count}|${sections_found}|${fm_rich}|${file_size_kb}" >> "$SCORES_FILE"
done < "$AGENT_LIST_FILE"

# ---- Aggregate and display ----
if [[ ! -s "$SCORES_FILE" ]]; then
  echo "No agents scored."
  exit 0
fi

# Count grades
count_a=0; count_b=0; count_c=0; count_d=0
total_scored=0

# Collect scores for sorting
score_entries=()
while IFS='|' read -r score grade agent_id cat wc sec fm fs; do
  if [[ "$score" == "SKIP" ]]; then
    continue
  fi
  total_scored=$((total_scored + 1))
  case "$grade" in
    A) count_a=$((count_a + 1)) ;;
    B) count_b=$((count_b + 1)) ;;
    C) count_c=$((count_c + 1)) ;;
    D) count_d=$((count_d + 1)) ;;
  esac

  # Store entry for sorting: "SCORE|AGENT_ID|CATEGORY"
  score_entries+=("${score}|${agent_id}|${cat}")
done < "$SCORES_FILE"

# ---- Category averages ----
# Gather category totals
cat_totals=()
cat_counts=()
while IFS='|' read -r score grade agent_id cat rest; do
  if [[ "$score" == "SKIP" ]]; then
    continue
  fi
  # Accumulate per category using indexed arrays
  found=-1
  for i in "${!cat_counts[@]}"; do
    if [[ "${cat_counts[$i]}" == "${cat}" ]]; then
      found=$i
      break
    fi
  done
  # We need a different approach: store category|score pairs and aggregate after
  echo "${cat}|${score}" >> "${SCORES_FILE}.cats"
done < "$SCORES_FILE"

# Calculate category averages using python3
echo "Score Distribution:"

# Calculate percentages and bar widths
if [[ "$total_scored" -gt 0 ]]; then
  pct_a=$(python3 -c "print(int(round(${count_a} * 100.0 / ${total_scored})))")
  pct_b=$(python3 -c "print(int(round(${count_b} * 100.0 / ${total_scored})))")
  pct_c=$(python3 -c "print(int(round(${count_c} * 100.0 / ${total_scored})))")
  pct_d=$(python3 -c "print(int(round(${count_d} * 100.0 / ${total_scored})))")

  # Bar: each block = 2%
  bar_a=$(python3 -c "print('█' * int(round(${count_a} * 100.0 / ${total_scored} / 2)))")
  bar_b=$(python3 -c "print('█' * int(round(${count_b} * 100.0 / ${total_scored} / 2)))")
  bar_c=$(python3 -c "print('█' * int(round(${count_c} * 100.0 / ${total_scored} / 2)))")
  bar_d=$(python3 -c "print('█' * int(round(${count_d} * 100.0 / ${total_scored} / 2)))")

  printf "  A (8-10):  %3d (%2d%%)  %s\n" "$count_a" "$pct_a" "$bar_a"
  printf "  B (5-7):   %3d (%2d%%)  %s\n" "$count_b" "$pct_b" "$bar_b"
  printf "  C (3-4):   %3d (%2d%%)  %s\n" "$count_c" "$pct_c" "$bar_c"
  printf "  D (0-2):   %3d (%2d%%)  %s\n" "$count_d" "$pct_d" "$bar_d"
fi
echo ""

# ---- Top 10 ----
echo "Top 10 Highest Scoring:"
sort -t'|' -k1 -nr "$SCORES_FILE" 2>/dev/null | head -10 | while IFS='|' read -r score grade agent_id cat wc sec fm fs; do
  if [[ "$score" == "SKIP" ]]; then continue; fi
  printf "  %s (%s/10) — %s\n" "$agent_id" "$score" "$cat"
done | awk 'BEGIN{i=1} {printf "  %2d. %s\n", i, $0; i++}'
echo ""

# ---- Bottom 10 ----
echo "Bottom 10 Lowest Scoring:"
sort -t'|' -k1 -n "$SCORES_FILE" 2>/dev/null | head -10 | while IFS='|' read -r score grade agent_id cat wc sec fm fs; do
  if [[ "$score" == "SKIP" ]]; then continue; fi
  printf "  %s (%s/10) — %s\n" "$agent_id" "$score" "$cat"
done | awk 'BEGIN{i=1} {printf "  %2d. %s\n", i, $0; i++}'
echo ""

# ---- Category Averages ----
SCORES_CATS_PY=$(resolve_py_path "${SCORES_FILE}.cats")
echo "Category Averages:"
if [[ -f "${SCORES_FILE}.cats" && -s "${SCORES_FILE}.cats" ]]; then
  python3 -c "
from collections import defaultdict
data = open('${SCORES_CATS_PY}').read().strip().splitlines()
cat_scores = defaultdict(list)
for line in data:
    if not line.strip(): continue
    parts = line.split('|')
    if len(parts) != 2: continue
    cat, sc = parts
    cat_scores[cat].append(int(sc))

for cat in sorted(cat_scores.keys()):
    scores = cat_scores[cat]
    avg = sum(scores) / len(scores)
    print('  {:<28s} {:.1f} ({} agents)'.format(cat + ':', avg, len(scores)))
" || true
fi
echo ""

# ---- Perimeter stats ----
# Count files < 100 words
short_count=$(awk -F'|' '$5!="SKIP" && $5+0<100' "$SCORES_FILE" 2>/dev/null | wc -l | tr -d ' ')
short_count="${short_count:-0}"

# Top 5 categories by count
echo "Largest Categories:"
if [[ -f "${SCORES_FILE}.cats" && -s "${SCORES_FILE}.cats" ]]; then
  python3 -c "
from collections import Counter
data = open('${SCORES_CATS_PY}').read().strip().splitlines()
cats = Counter()
for line in data:
    if not line.strip(): continue
    parts = line.split('|')
    if len(parts) != 2: continue
    cats[parts[0]] += 1
for cat, n in cats.most_common(5):
    print('  {:<24s} {} agents'.format(cat, n))
" || true
fi
echo ""

# ---- Quality Gate ----
ab_total=$(( count_a + count_b ))
ab_pct=0
if [[ "$total_scored" -gt 0 ]]; then
  ab_pct=$(python3 -c "print(int(round(${ab_total} * 100.0 / ${total_scored})))")
fi

if [[ "$ab_pct" -ge 60 ]]; then
  echo "═══ PASS: Quality gate met (${ab_pct}% agents grade A/B)"
else
  echo "═══ FAIL: Quality gate not met (${ab_pct}% agents grade A/B, need >= 60%)"
fi

# Cleanup temp files
rm -f "${SCORES_FILE}.cats"

# --threshold: exit 1 if any agent scored below threshold (for CI)
if [[ "$THRESHOLD" -gt 0 ]]; then
  below_threshold=0
  while IFS="|" read -r score rest; do
    [[ "$score" == "SKIP" ]] && continue
    if [[ "$score" -lt "$THRESHOLD" ]]; then
      below_threshold=$((below_threshold + 1))
    fi
  done < "$SCORES_FILE"
  if [[ "$below_threshold" -gt 0 ]]; then
    echo "THRESHOLD FAIL: ${below_threshold} agent(s) scored below ${THRESHOLD} (minimum grade $([ "$THRESHOLD" -ge 8 ] && echo A || [ "$THRESHOLD" -ge 5 ] && echo B || [ "$THRESHOLD" -ge 3 ] && echo C || echo D))"
    exit 1
  else
    echo "THRESHOLD PASS: all agents score >= ${THRESHOLD}"
  fi
fi
