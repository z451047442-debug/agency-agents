#!/usr/bin/env bash
#
# suggest-nexus-roles.sh — Propose nexus_roles for agents based on content analysis.
#
# Scans each agent's body for phase-related keywords and suggests which
# NEXUS pipeline phases the agent should participate in.
#
# Usage:
#   ./scripts/suggest-nexus-roles.sh [--category name] [--file path] [--min-confidence N]
#
#   --category name       Only analyze one category
#   --file path           Analyze a single agent file
#   --min-confidence N    Minimum keyword match count to suggest (default: 2)
#   --apply               Write suggestions into agent files (prompts for confirmation)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CATEGORY_FILTER=""
SINGLE_FILE=""
MIN_CONFIDENCE=2
APPLY=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --category|-c)       CATEGORY_FILTER="$2"; shift 2 ;;
    --file|-f)           SINGLE_FILE="$2"; shift 2 ;;
    --min-confidence)    MIN_CONFIDENCE="$2"; shift 2 ;;
    --apply)             APPLY=true; shift ;;
    --help|-h)
      echo "Usage: suggest-nexus-roles.sh [--category name] [--file path] [--min-confidence N] [--apply]"
      echo "Analyzes agent content and suggests NEXUS phase assignments."
      echo "  --min-confidence N  Minimum keyword matches to suggest a phase (default: 2)"
      echo "  --apply             Write suggestions into frontmatter (asks for confirmation)"
      exit 0 ;;
    *) shift ;;
  esac
done

# Phase keyword definitions
declare -A PHASE_KEYWORDS
PHASE_KEYWORDS[phase-0-discovery]="research|market analysis|user research|discovery|competitive|audit|assess|landscape|investigate|explore|survey|interview|persona|journey map|benchmark"
PHASE_KEYWORDS[phase-1-strategy]="strategy|architecture|planning|roadmap|design system|information architecture|blueprint|specification|scope|requirements|architecture decision|system design|trade-off"
PHASE_KEYWORDS[phase-2-foundation]="scaffolding|setup|bootstrap|configuration|CI/CD|environment|project init|repository|infrastructure|provision|foundation|pipeline|deployment|monitoring setup"
PHASE_KEYWORDS[phase-3-build]="development|implementation|coding|building|construction|create|develop|write code|deploy|implement|build|programming|engineering|feature|component"
PHASE_KEYWORDS[phase-4-hardening]="testing|QA|security review|performance|optimization|hardening|code review|linting|audit|quality|vulnerability|validation|verification|benchmark|refactor"
PHASE_KEYWORDS[phase-5-launch]="launch|release|deployment|go-live|production|rollout|migration|announcement|go-to-market|ship|publish|delivery"
PHASE_KEYWORDS[phase-6-operate]="monitoring|maintenance|support|operations|incident|SRE|observability|iteration|continuous improvement|feedback|metrics|analytics|reporting"

# Phase labels for display
declare -A PHASE_LABELS
PHASE_LABELS[phase-0-discovery]="Discovery"
PHASE_LABELS[phase-1-strategy]="Strategy"  
PHASE_LABELS[phase-2-foundation]="Foundation"
PHASE_LABELS[phase-3-build]="Build"
PHASE_LABELS[phase-4-hardening]="Hardening"
PHASE_LABELS[phase-5-launch]="Launch"
PHASE_LABELS[phase-6-operate]="Operate"

# Collect files
files=()
if [[ -n "$SINGLE_FILE" ]]; then
  files=("$SINGLE_FILE")
elif [[ -n "$CATEGORY_FILTER" ]]; then
  while IFS= read -r f; do files+=("$f"); done < <(find "$REPO_ROOT/$CATEGORY_FILTER" -maxdepth 2 -name "*.md" -type f | sort)
else
  source "$SCRIPT_DIR/_discover_dirs.sh"
  AGENT_DIRS=()
  while IFS= read -r d; do AGENT_DIRS+=("$d"); done < <(discover_agent_dirs)
  for dir in "${AGENT_DIRS[@]}"; do
    while IFS= read -r f; do files+=("$f"); done < <(find "$REPO_ROOT/$dir" -maxdepth 2 -name "*.md" -type f | sort)
  done
fi

analyzed=0; suggested=0
for file in "${files[@]}"; do
  # Skip non-agent files
  head -1 "$file" | grep -q "^---$" || continue
  
  # Extract body
  body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$file")
  body_lower=$(echo "$body" | tr '[:upper:]' '[:lower:]')
  
  agent_id=$(basename "$file" .md)
  matches=""
  
  for phase in phase-0-discovery phase-1-strategy phase-2-foundation phase-3-build phase-4-hardening phase-5-launch phase-6-operate; do
    count=0
    for kw in $(echo "${PHASE_KEYWORDS[$phase]}" | tr '|' '\n'); do
      if echo "$body_lower" | grep -qw "$kw" 2>/dev/null; then
        count=$((count + 1))
      fi
    done
    if [[ "$count" -ge "$MIN_CONFIDENCE" ]]; then
      matches="$matches  - $phase  # ${PHASE_LABELS[$phase]} ($count keywords)"
$'\n'
    fi
  done
  
  if [[ -n "$matches" ]]; then
    suggested=$((suggested + 1))
    echo "── $agent_id ──"
    echo "$matches"
  fi
  analyzed=$((analyzed + 1))
done

echo ""
echo "Analyzed: $analyzed | Suggested: $suggested | Min confidence: $MIN_CONFIDENCE"
echo "Run with --apply to write suggestions into agent frontmatter."
