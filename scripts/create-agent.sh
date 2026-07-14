#!/usr/bin/env bash
#
# create-agent.sh — Scaffolds a new Agency agent .md file
#
# Usage:
#   ./scripts/create-agent.sh                                    # interactive
#   ./scripts/create-agent.sh --name "..." --category ... ... --emoji ... --color ...  # CLI
#   ./scripts/create-agent.sh --list-categories                  # list categories
#
# Requirements: bash 3.2+, running from the repo root.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
AGENTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LINT_SCRIPT="$SCRIPT_DIR/lint-agents.sh"

# ---------------------------------------------------------------------------
# Named CSS colours accepted by the project schema
# ---------------------------------------------------------------------------
VALID_NAMED_COLORS="cyan blue green red purple orange teal indigo pink gold amber yellow violet rose lime gray fuchsia navy slate brown"

# ANSI escape helpers (printf-based for macOS bash 3.2 compat)
BOLD="$(printf '\033[1m')"
GREEN="$(printf '\033[32m')"
YELLOW="$(printf '\033[33m')"
RED="$(printf '\033[31m')"
CYAN="$(printf '\033[36m')"
RESET="$(printf '\033[0m')"

# Helpers
info()    { printf "%b"  "${CYAN}[info]${RESET}  $*\n"; }
success() { printf "%b"  "${GREEN}[ok]${RESET}    $*\n"; }
warn()    { printf "%b"  "${YELLOW}[warn]${RESET}   $*\n"; }
error()   { printf "%b"  "${RED}[error]${RESET}  $*\n" >&2; }

# Auto-discover agent directories (shared logic — see _discover_dirs.sh)
REPO_ROOT="$AGENTS_DIR"
source "$SCRIPT_DIR/_discover_dirs.sh"

# Discover agent category directories (uses shared discover_agent_dirs)
get_categories() {
  discover_agent_dirs
}

validate_category() {
  local cat="$1" cat_list
  cat_list="$(get_categories)"
  if ! printf '%s\n' "$cat_list" | grep -qxF "$cat"; then
    error "Unknown category: '$cat'.  Run --list-categories to see valid choices."
    return 1
  fi
}

validate_emoji() {
  local em="$1"
  local len="${#em}"
  if [[ "$len" -lt 1 || "$len" -gt 4 ]]; then
    error "Emoji must be 1-4 characters, got '${em}' (${len} chars)."
    return 1
  fi
}

validate_color() {
  local c="$1"
  [[ "$c" =~ ^#[0-9a-fA-F]{3,6}$ ]] && return 0
  local nc
  for nc in $VALID_NAMED_COLORS; do
    [[ "$c" = "$nc" ]] && return 0
  done
  error "Invalid colour: '$c'.  Use a named colour (${VALID_NAMED_COLORS// /, }) or #RRGGBB."
  return 1
}

# Generate agent-id: lowercase, spaces-to-hyphens, category-prefixed
slugify() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[[:space:]]\+/-/g;s/[^a-z0-9-]//g;s/-\+/-/g;s/^-//;s/-$//'
}

make_agent_id() {
  printf '%s-%s' "$1" "$(slugify "$2")"
}

# Write the agent .md file with all required sections + placeholder content
write_agent_file() {
  local filepath="$1" name="$2" description="$3" emoji="$4" color="$5" vibe="$6" cat="$7"
  local today
  today=$(date +%Y-%m-%d 2>/dev/null || printf '%s' "$(date +%Y-%m-%d)")
  cat > "$filepath" <<AGENTEOF
---
name: "${name}"
description: "${description}"
emoji: ${emoji}
color: ${color}
version: "1.0.0"
date_added: "${today}"
vibe: ${vibe}
---

# ${emoji} ${name} Agent

## 🧠 Your Identity & Memory

You are **[Persona Name]**, a [role] with [X]+ years of experience in [specific domain]. You've [key accomplishment 1 — something measurable], [key accomplishment 2 — a challenge you solved], and learned that [key insight — a non-obvious truth about your field].

You think in **[core frameworks or mental models]**. Your domain answers: [key question 1]? [key question 2]? [key question 3]?

**You remember and carry forward:**
- [Domain principle 1 — a methodology or rule of thumb you always apply]
- [Domain principle 2 — a common pitfall and how you avoid it]
- [Domain principle 3 — a metric or framework you use to evaluate situations]

## 🎯 Your Core Mission

[One sentence summary of what you do and for whom]

### Primary Capabilities
1. **[Capability 1]**: [Specific task or analysis you perform — include concrete examples]
2. **[Capability 2]**: [Specific task or analysis you perform]
3. **[Capability 3]**: [Specific task or analysis you perform]
4. **[Capability 4]**: [Specific task or analysis you perform]

## 🎯 Your Success Metrics

- **[Metric 1]**: [What you measure and what good looks like — be specific]
- **[Metric 2]**: [What you measure and what good looks like]
- **[Metric 3]**: [What you measure and what good looks like]
- **[Metric 4]**: [What you measure and what good looks like]

## 🚨 Critical Rules You Must Follow

1. **Stay in your domain.** Provide advice only within your area of expertise. If asked about topics outside your knowledge, clearly state your limitations.
2. **Be specific and actionable.** Every recommendation must include concrete steps, not just general principles.
3. **[Domain Rule 1]**: [A rule specific to your field — what you must always do or never do]
4. **[Domain Rule 2]**: [A rule specific to your field]
5. **[Domain Rule 3]**: [A rule specific to your field]

## 💬 Your Communication Style

- **[Trait 1]**: [How you apply this in responses — give an example]
- **[Trait 2]**: [How you apply this in responses]
- **[Trait 3]**: [How you apply this in responses]
- **[Trait 4]**: [How you apply this in responses]

## 📦 Deliverables

Based on your mission and expertise, you produce:

- **Analysis & Assessment**: [Specific type of analysis you deliver]
- **Recommendations**: [Specific type of recommendations you make]
- **Documentation**: [Specific documentation you create]
- **Implementation Guidance**: [How you support execution]

## 🔄 Your Workflow

1. **Understand**: [How you gather context, requirements, and constraints]
2. **Analyze**: [How you apply your domain expertise to evaluate the situation]
3. **Recommend**: [How you formulate specific, actionable guidance with clear rationale]
4. **Support**: [How you help with implementation, follow-up, and iteration]

---

**Instructions Reference**: Your [domain] methodology is built on [X]+ years of [field]. [Key principle 1], [key principle 2], [key principle 3], and [key principle 4].
AGENTEOF
}

# Run lint-agents.sh on the new file
run_lint() {
  local filepath="$1"
  if [[ -x "$LINT_SCRIPT" ]]; then
    info "Running lint-agents.sh on new file..."
    bash "$LINT_SCRIPT" "$filepath" || true
  else
    warn "lint-agents.sh not found or not executable — skipping validation."
  fi
}

# Post-creation quality check — warns if the agent is still mostly placeholders
quality_check() {
  local filepath="$1"
  local body word_count filled fraction

  # Extract body (after second ---)
  body=$(awk 'BEGIN{n=0} /^---$/{n++; next} n>=2{print}' "$filepath")
  word_count=$(printf '%s' "$body" | wc -w | tr -d ' ')
  word_count="${word_count:-0}"

  # Count how many placeholders (lines with [bracketed text]) remain
  filled=$(printf '%s' "$body" | grep -cvE '^[[:space:]]*(-|\#|\*\*)*[[:space:]]*\[.*\]' || echo 0)
  total_lines=$(printf '%s' "$body" | grep -c . || echo 1)
  fraction=$(( filled * 100 / total_lines ))

  echo ""
  printf "%b\n" "${BOLD}── Post-Creation Quality Check ──${RESET}"
  printf "  Word count:       %s words\n" "$word_count"

  if [[ "$word_count" -lt 400 ]]; then
    printf "  %b\n" "${YELLOW}⚠ Content is underweight (target: 400+ words for B-grade, 800+ for A-grade)${RESET}"
  elif [[ "$word_count" -lt 800 ]]; then
    printf "  %b\n" "${CYAN}✓ Content is adequate for B-grade (target 800+ for A-grade)${RESET}"
  else
    printf "  %b\n" "${GREEN}✓ Content depth is A-grade ready${RESET}"
  fi

  if [[ "$fraction" -lt 70 ]]; then
    printf "  %b\n" "${RED}⚠ ~$((100 - fraction))%% of lines are still placeholders — fill all [bracketed] sections${RESET}"
  elif [[ "$fraction" -lt 90 ]]; then
    printf "  %b\n" "${YELLOW}⚠ Some placeholders remain — review [bracketed] sections${RESET}"
  fi

  printf "\n%b\n" "${CYAN}  Sections to complete before publishing:${RESET}"
  printf "    1. Replace [Persona Name] with a real name\n"
  printf "    2. Fill in domain-specific rules (not just the generic ones)\n"
  printf "    3. Define concrete success metrics with measurable targets\n"
  printf "    4. Replace all [bracketed placeholders] with real content\n"
  printf "    5. Add a real 'Instructions Reference' summary\n"

  printf "\n%b\n" "${CYAN}  Tip: Run 'python scripts/expand-agent.py \$(basename $filepath .md)' for a structured expansion plan.${RESET}"
  printf "%b\n" "${BOLD}─────────────────────────────────────${RESET}"
}

# Interactive mode
interactive_mode() {
  printf "%b\n" "${BOLD}Agency Agent Scaffolder${RESET}\n"

  # 1. Category
  local categories
  categories=$(get_categories)
  printf "Available categories:\n"
  printf '%s' "$categories" | column
  printf "\n"
  while true; do
    printf "Category: "
    read -r category
    validate_category "$category" 2>/dev/null && break
  done

  # 2. Agent name
  while true; do
    printf "Agent name (display name, e.g. 'K8s Expert'): "
    read -r name
    name=$(printf '%s' "$name" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    [[ -n "$name" ]] && break || error "Name cannot be empty."
  done

  # 3. Description
  while true; do
    printf "Description (one sentence, 10-500 chars): "
    read -r description
    description=$(printf '%s' "$description" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    local dlen="${#description}"
    if [[ "$dlen" -lt 10 ]]; then
      error "Description must be at least 10 characters (got ${dlen})."
    elif [[ "$dlen" -gt 500 ]]; then
      error "Description must be at most 500 characters (got ${dlen})."
    else
      break
    fi
  done

  # 4. Emoji
  while true; do
    printf "Emoji (1-4 chars): "
    read -r emoji
    emoji=$(printf '%s' "$emoji" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    validate_emoji "$emoji" 2>/dev/null && break
  done

  # 5. Colour
  while true; do
    printf "Colour (named or #RRGGBB): "
    read -r color
    color=$(printf '%s' "$color" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
    validate_color "$color" 2>/dev/null && break
  done

  # 6. Vibe (optional)
  printf "Vibe (one-line personality primer, optional): "
  read -r vibe
  vibe=$(printf '%s' "$vibe" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

  do_create "$category" "$name" "$description" "$emoji" "$color" "$vibe"
}

# Shared creation logic
do_create() {
  local category="$1" name="$2" description="$3" emoji="$4" color="$5" vibe="${6:-}"
  local agent_id filepath

  validate_category "$category" || exit 1
  validate_emoji "$emoji"     || exit 1
  validate_color "$color"     || exit 1

  agent_id=$(make_agent_id "$category" "$name")
  filepath="$AGENTS_DIR/${category}/${agent_id}.md"

  if [[ -f "$filepath" ]]; then
    warn "File already exists: ${filepath} — will be overwritten."
    printf "Overwrite? [y/N] "
    read -r confirm
    [[ "$confirm" = "y" || "$confirm" = "Y" ]] || { info "Aborted."; exit 0; }
  fi

  info "Creating agent: ${agent_id}"
  info "  File:       ${filepath}"

  write_agent_file "$filepath" "$name" "$description" "$emoji" "$color" "$vibe" "$category"

  success "Agent file created: ${filepath}"
  run_lint "$filepath"
  quality_check "$filepath"
}

# CLI mode
cli_mode() {
  local name="" category="" emoji="" color="" description="" vibe=""

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --name)        name="$2";        shift 2 ;;
      --category)    category="$2";    shift 2 ;;
      --emoji)       emoji="$2";       shift 2 ;;
      --color)       color="$2";       shift 2 ;;
      --description) description="$2"; shift 2 ;;
      --vibe)        vibe="$2";        shift 2 ;;
      *)
        error "Unknown flag: $1"
        printf "Usage: %s --name \"...\" --category ... --emoji ... --color ... [--description ...] [--vibe ...]\n" "$0"
        exit 1 ;;
    esac
  done

  # Check required
  local missing=""
  [[ -z "$name" ]]     && missing="${missing} --name"
  [[ -z "$category" ]] && missing="${missing} --category"
  [[ -z "$emoji" ]]    && missing="${missing} --emoji"
  [[ -z "$color" ]]    && missing="${missing} --color"
  if [[ -n "$missing" ]]; then
    error "Missing required flags:${missing}"
    exit 1
  fi

  [[ -z "$description" ]] && description="Expert in ${category} — ${name}"

  do_create "$category" "$name" "$description" "$emoji" "$color" "$vibe"
}

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------
cd "$AGENTS_DIR"

if [[ $# -eq 0 ]]; then
  interactive_mode
elif [[ "$1" = "--list-categories" ]]; then
  get_categories
  exit 0
else
  cli_mode "$@"
fi
