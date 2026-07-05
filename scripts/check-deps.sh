#!/usr/bin/env bash
#
# Validates depends_on references in agent frontmatter against AGENTS.json.
#
# Usage: ./scripts/check-deps.sh [--manifest]

set -euo pipefail

MANIFEST_MODE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) MANIFEST_MODE=true; shift ;;
    --help|-h)
      echo "Usage: check-deps.sh [--manifest]"
      echo "  --manifest  Output depends_on.json manifest to stdout"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INDEX="$REPO_ROOT/AGENTS.json"

if [[ ! -f "$INDEX" ]]; then
  echo "ERROR: AGENTS.json not found at $INDEX"
  echo "Run: ./scripts/generate-index.sh"
  exit 1
fi

# Resolve path for native Python on Windows (Git Bash / MSYS2)
if command -v cygpath &>/dev/null; then
  INDEX_PY=$(cygpath -m "$INDEX")
else
  INDEX_PY="$INDEX"
fi

# Build set of valid agent IDs from AGENTS.json
VALID_IDS_FILE=$(mktemp)
trap 'rm -f "$VALID_IDS_FILE" "${VALID_IDS_FILE}.deps"' EXIT

python3 -c "
import json
d = json.load(open('$INDEX_PY', encoding='utf-8'))
for a in d['agents']:
    print(a['id'])
" > "$VALID_IDS_FILE"

echo "=== Dependency Check ==="

# Auto-discover agent directories (shared logic — see _discover_dirs.sh)
source "$SCRIPT_DIR/_discover_dirs.sh"
AGENT_DIRS=()
while IFS= read -r d; do
  AGENT_DIRS+=("$d")
done < <(discover_agent_dirs)

# Find files with depends_on
files_with_deps=()
for dir in "${AGENT_DIRS[@]}"; do
  while IFS= read -r f; do
    # Check if frontmatter contains depends_on:
    frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$f" 2>/dev/null || true)
    if echo "$frontmatter" | grep -qE '^depends_on:'; then
      files_with_deps+=("$f")
    fi
  done < <(find "$REPO_ROOT/$dir" -maxdepth 2 -name "*.md" -type f 2>/dev/null | sort)
done

if [[ ${#files_with_deps[@]} -eq 0 ]]; then
  echo "Agents with dependencies: 0"
  echo ""
  echo "No depends_on references found in any agent files."
  exit 0
fi

echo "Agents with dependencies: ${#files_with_deps[@]}"

if $MANIFEST_MODE; then
  echo '{'
  m_count=0
  # Count agents with actual deps
  for ff in "${files_with_deps[@]}"; do
    m_fm_tmp=$(awk 'NR==1{next} /^---$/{exit} {print}' "$ff" 2>/dev/null || true)
    m_has=0
    m_dl=$(echo "$m_fm_tmp" | awk '/^depends_on:/{flag=1; next} flag && /^  - /{print; next} flag && !/^  /{exit}')
    [[ -n "$m_dl" ]] && m_has=1
    [[ $m_has -eq 0 ]] && { m_dl2=$(echo "$m_fm_tmp" | grep -E '^depends_on:[[:space:]]+[^[:space:]]' | head -1); [[ -n "$m_dl2" ]] && m_has=1; }
    [[ $m_has -eq 1 ]] && m_count=$((m_count + 1))
  done
  m_i=0
  for file in "${files_with_deps[@]}"; do
    rel_path="${file#$REPO_ROOT/}"
    m_id="$(basename "$rel_path" .md)"
    m_fm=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file")
    m_deps=()
    m_dep_list=$(echo "$m_fm" | awk '/^depends_on:/{flag=1; next} flag && /^  - /{print; next} flag && !/^  /{exit}')
    if [[ -n "$m_dep_list" ]]; then
      while IFS= read -r dline; do
        val=$(echo "$dline" | sed 's/^  - //' | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//" | xargs)
        [[ -n "$val" ]] && m_deps+=("$val")
      done <<< "$m_dep_list"
    else
      m_dep_line=$(echo "$m_fm" | grep -E '^depends_on:' | head -1)
      if [[ -n "$m_dep_line" ]]; then
        m_dep_val=$(echo "$m_dep_line" | sed 's/^depends_on:[[:space:]]*//')
        if [[ -n "$m_dep_val" ]]; then
          IFS=',' read -ra m_raw_deps <<< "$m_dep_val"
          for m_raw in "${m_raw_deps[@]}"; do
            m_trimmed=$(echo "$m_raw" | xargs)
            [[ -n "$m_trimmed" ]] && m_deps+=("$m_trimmed")
          done
        fi
      fi
    fi
    if [[ ${#m_deps[@]} -gt 0 ]]; then
      m_i=$((m_i + 1))
      m_json_deps=$(printf '%s\n' "${m_deps[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo '[]')
      if [[ $m_i -lt $m_count ]]; then
        echo "  \"$m_id\": $m_json_deps,"
      else
        echo "  \"$m_id\": $m_json_deps"
      fi
    fi
  done
  echo '}'
  exit 0
fi

echo ""

total_deps=0
valid_deps=0
broken_deps=0
broken_entries=()

# Process each file with dependencies
for file in "${files_with_deps[@]}"; do
  rel_path="${file#$REPO_ROOT/}"
  frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file")

  # Extract depends_on values. Handle two formats:
  #   1. Single-line: depends_on: id1, id2, id3
  #   2. YAML list:   depends_on:\n  - id1\n  - id2
  deps=()

  # First try YAML list format (multi-line)
  dep_list=$(echo "$frontmatter" | awk '/^depends_on:/{flag=1; next} flag && /^  - /{print; next} flag && !/^  /{exit}')

  if [[ -n "$dep_list" ]]; then
    # YAML list: each line is "  - agent-id"
    while IFS= read -r line; do
      dep_val=$(echo "$line" | sed 's/^  - //' | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//")
      dep_val=$(echo "$dep_val" | xargs)  # trim whitespace
      if [[ -n "$dep_val" ]]; then
        deps+=("$dep_val")
      fi
    done <<< "$dep_list"
  else
    # Try single-line format: depends_on: val1, val2, val3
    dep_line=$(echo "$frontmatter" | grep -E '^depends_on:' | head -1)
    if [[ -n "$dep_line" ]]; then
      dep_val=$(echo "$dep_line" | sed 's/^depends_on:[[:space:]]*//' | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//")
      if [[ -n "$dep_val" ]]; then
        # Split by commas
        IFS=',' read -ra raw_deps <<< "$dep_val"
        for raw in "${raw_deps[@]}"; do
          trimmed=$(echo "$raw" | xargs)
          if [[ -n "$trimmed" ]]; then
            deps+=("$trimmed")
          fi
        done
      fi
    fi
  fi

  if [[ ${#deps[@]} -eq 0 ]]; then
    continue
  fi

  # Print file header
  echo "  ${rel_path}"

  for dep in "${deps[@]}"; do
    total_deps=$((total_deps + 1))
    if grep -qxF "$dep" "$VALID_IDS_FILE"; then
      echo "    depends_on: ${dep} ✅"
      valid_deps=$((valid_deps + 1))
    else
      echo "    depends_on: ${dep} ❌ NOT FOUND"
      broken_deps=$((broken_deps + 1))
      broken_entries+=("${rel_path}:${dep}")
    fi
  done
  echo ""
done

# Summary
echo "═══ ${valid_deps}/${total_deps} dependencies valid"

if [[ "$broken_deps" -gt 0 ]]; then
  echo "═══ ${broken_deps} broken"
  echo ""
  echo "Broken references:"
  for entry in "${broken_entries[@]}"; do
    file_part="${entry%%:*}"
    dep_part="${entry#*:}"
    echo "  ${file_part} → ${dep_part}"
  done
  exit 1
else
  echo "═══ All dependencies valid"
  exit 0
fi
