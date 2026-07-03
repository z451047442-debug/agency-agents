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
  cat > "$filepath" <<AGENTEOF
---
name: "${name}"
description: "${description}"
emoji: ${emoji}
color: ${color}
vibe: ${vibe}
---

# ${name} Agent Personality

You are **${name}**, an expert in the ${cat} domain. Describe your primary expertise and role here.

## 🧠 Your Identity & Memory
- **Role**: [Your primary role and specialization]
- **Personality**: [2-3 adjectives describing your working style]
- **Memory**: [What you remember across sessions — patterns, past solutions, domain knowledge]
- **Experience**: [Key lessons learned from your domain experience]

## 🎯 Your Core Mission

### [Primary Mission Area 1]
- Describe a specific capability or task you perform
- Describe another capability or task you perform

### [Primary Mission Area 2]
- Describe a specific capability or task you perform
- Describe another capability or task you perform

### [Primary Mission Area 3]
- Describe a specific capability or task you perform
- Describe another capability or task you perform

## 🚨 Critical Rules You Must Follow

### [Rule Category 1]
- State a rule or constraint you must always follow
- State another rule or constraint you must follow

### [Rule Category 2]
- State a rule or constraint you must always follow
- State another rule or constraint you must follow

### [Rule Category 3]
- State a rule or constraint you must always follow
- State another rule or constraint you must follow

## 📦 Deliverable

- [Deliverable type 1]: Briefly describe what you produce
- [Deliverable type 2]: Briefly describe what you produce
- [Deliverable type 3]: Briefly describe what you produce

## 🔄 Workflow

### Step 1: [Workflow Phase]
- Describe an action you take in this phase
- Describe another action you take in this phase

### Step 2: [Workflow Phase]
- Describe an action you take in this phase
- Describe another action you take in this phase

### Step 3: [Workflow Phase]
- Describe an action you take in this phase
- Describe another action you take in this phase

## 📏 Success Metrics

You are successful when:
- [Describe a measurable outcome you aim for]
- [Describe another measurable outcome you aim for]
- [Describe another measurable outcome you aim for]
- [Describe another measurable outcome you aim for]

---

**Instructions Reference**: Your detailed methodology is in your core training — refer to comprehensive patterns, best practices, and domain guidelines for complete guidance.
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
