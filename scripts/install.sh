#!/usr/bin/env bash
#
# --- USAGE-START ---  (sentinel for usage(); do not remove)
# install.sh -- Install The Agency agents into your local agentic tool(s).
#
# Reads converted files from integrations/ and copies them to the appropriate
# config directory for each tool. Run scripts/convert.sh first if integrations/
# is missing or stale.
#
# Usage:
#   ./scripts/install.sh [selection] [mode] [behavior]
#   Bare invocation installs all agents to detected tools (interactive when a TTY).
#   ./scripts/install.sh [--tool <name>] [--interactive] [--no-interactive] [--parallel] [--jobs N]
#                         [--uninstall] [--list-installed] [--agent <id>] [--help]
#
# Tools:
#   claude-code  -- Copy agents to ~/.claude/agents/
#   copilot      -- Copy agents to ~/.github/agents/ and ~/.copilot/agents/
#   antigravity  -- Copy skills to ~/.gemini/antigravity/skills/
#   gemini-cli   -- Install agents to ~/.gemini/agents/
#   opencode     -- Copy agents to .opencode/agents/ in current directory
#   cursor       -- Copy rules to .cursor/rules/ in current directory
#   aider        -- Copy CONVENTIONS.md to current directory
#   windsurf     -- Copy .windsurfrules to current directory
#   openclaw     -- Copy workspaces to ~/.openclaw/agency-agents/
#   qwen         -- Copy SubAgents to ~/.qwen/agents/ (user-wide) or .qwen/agents/ (project)
#   codex        -- Copy custom agent TOML files to ~/.codex/agents/
#   osaurus      -- Copy skills to ~/.osaurus/skills/
#   hermes       -- Copy lazy-router plugin to ~/.hermes/plugins/ and enable it
#   all          -- Install for all detected tools (default)
#
# Selection (compose freely; empty = everything):
#   --tool <a,b>          Only these tools
#   --division <a,b>      Only these teams/divisions (comma-separated)
#   --agent <slug,slug>   Only these specific agents
#   --agents-file <path>  Agents listed in a file (one slug/name per line, # comments ok)
#
# Mode:
#   --link                Symlink instead of copy (updates propagate)
#   --path <dir>          Override the install directory (single destination)
#
# Behavior:
#   --interactive         Show the interactive wizard (default when run in a terminal)
#   --no-interactive      Skip the wizard, install all detected tools
#   --no-convert          Don't auto-run convert.sh when integration files are missing
#   --dry-run             Print the plan and exit without writing anything
#   --list [tools|teams|agents]   List and exit
#   --parallel            Install tools in parallel (output buffered per tool)
#   --jobs N              Max parallel jobs (default: nproc or 4)
#   --help                Show this help
#
# Env: CLAUDE_CONFIG_DIR, COPILOT_AGENT_DIR, CURSOR_RULES_DIR, GEMINI_AGENTS_DIR,
#      OPENCODE_AGENTS_DIR, OPENCLAW_DIR, QWEN_AGENTS_DIR, CODEX_AGENTS_DIR,
#      OSAURUS_SKILLS_DIR, HERMES_HOME, HERMES_PLUGIN_DIR
#      override default install paths (checked before hardcoded defaults).
#
# --- USAGE-END ---  (sentinel for usage(); do not remove)
# Platform support:
#   Linux, macOS (requires bash 3.2+), Windows Git Bash / WSL

set -euo pipefail

# ---------------------------------------------------------------------------
# Source shared infrastructure + per-tool modules
# ---------------------------------------------------------------------------
# Everything not specific to a single tool now lives in scripts/install/lib.sh.
# Per-tool install/uninstall functions live in scripts/install/install-<tool>.sh.
#
# lib.sh sets SCRIPT_DIR, REPO_ROOT, INTEGRATIONS, AGENT_DIRS, ALL_TOOLS,
# ALL_DIVISIONS, colour helpers, selection engine, tool detection, TUI wizard,
# generic uninstall/list/verify, and the install_tool/uninstall_tool dispatchers.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install/lib.sh"

# Per-tool modules (just function definitions, no side effects)
. "$_AGENCY_INSTALL_LIB_DIR/install-claude-code.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-copilot.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-antigravity.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-gemini-cli.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-opencode.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-openclaw.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-cursor.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-aider.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-windsurf.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-qwen.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-kimi.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-codex.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-osaurus.sh"
. "$_AGENCY_INSTALL_LIB_DIR/install-hermes.sh"

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
  # Extract everything between the USAGE-START / USAGE-END sentinels
  # (excluding the sentinel lines themselves) and strip the leading "# ".
  # Using sentinels instead of hard-coded line numbers means adding lines
  # to the header comment block won't silently break --help output.
  sed -n '/^# --- USAGE-START ---/,/^# --- USAGE-END ---/p' "$0" \
    | sed -e '1d;$d' -e 's/^# \{0,1\}//'
  exit 0
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
main() {
  local tool="all"
  local interactive_mode="auto"
  local use_parallel=false
  local warn_deps=true
  local verify_mode=false
  local uninstall_mode=false
  local list_mode=false
  local parallel_jobs
  parallel_jobs="$(parallel_jobs_default)"

  local list_what=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --tool)            tool="${2:?'--tool requires a value'}"; shift 2; interactive_mode="no" ;;
      --agent)
        if [[ "$2" =~ , ]]; then
          local _a
          IFS=',' read -ra _ags <<< "${2:?'--agent requires a value'}"
          for _a in "${_ags[@]}"; do
            _a="$(printf '%s' "$_a" | xargs)"; [[ -n "$_a" ]] && FILTER_AGENTS+=("$_a")
          done
        else
          single_agent="${2:?'--agent requires a value'}"
        fi
        shift 2 ;;
      --division)
        local _d
        IFS=',' read -ra _divs <<< "${2:?'--division requires a value'}"
        for _d in "${_divs[@]}"; do
          _d="$(printf '%s' "$_d" | xargs)"; [[ -z "$_d" ]] && continue
          FILTER_DIVISIONS+=("$_d")
        done
        interactive_mode="no"; shift 2 ;;
      --agents-file)     AGENTS_FILE="${2:?'--agents-file requires a value'}"; interactive_mode="no"; shift 2 ;;
      --link)            USE_LINK=true; shift ;;
      --path)            OVERRIDE_PATH="${2:?'--path requires a value'}"; shift 2 ;;
      --no-convert)      AUTO_CONVERT=false; shift ;;
      --dry-run)         DRY_RUN=true; interactive_mode="no"; shift ;;
      --list)            if [[ -z "${2:-}" || "${2:-}" == --* ]]; then list_what="all"; shift; else list_what="$2"; shift 2; fi ;;
      --interactive)     interactive_mode="yes"; shift ;;
      --no-interactive)  interactive_mode="no"; shift ;;
      --uninstall)       uninstall_mode=true; shift ;;
      --list-installed)  list_mode=true; shift ;;
      --parallel)        use_parallel=true; shift ;;
      --jobs)               parallel_jobs="${2:?'--jobs requires a value'}"; shift 2 ;;
      --warn-missing-deps)  warn_deps=true; shift ;;
      --verify)            verify_mode=true; shift ;;
      --help|-h)            usage ;;
      *)                    err "Unknown option: $1"; usage ;;
    esac
  done

  [[ -n "$list_what" ]] && { do_list "$list_what"; exit 0; }
  build_selection

  check_integrations

  # Validate explicit tool
  if [[ "$tool" != "all" ]]; then
    local valid=false t
    for t in "${ALL_TOOLS[@]}"; do [[ "$t" == "$tool" ]] && valid=true && break; done
    if ! $valid; then
      err "Unknown tool '$tool'. Valid: ${ALL_TOOLS[*]}"
      exit 1
    fi
  fi

  # --- List installed mode ---
  if $list_mode; then
    list_installed
    exit 0
  fi

  # --- Uninstall mode ---
  if $uninstall_mode; then
    if [[ "$tool" == "all" ]]; then
      # Uninstall from all detected tools
      header "The Agency -- Scanning for installed tools to uninstall..."
      SELECTED_TOOLS=()
      for t in "${ALL_TOOLS[@]}"; do
        is_detected "$t" && SELECTED_TOOLS+=("$t")
      done
      if [[ ${#SELECTED_TOOLS[@]} -eq 0 ]]; then
        info "No tools with agents detected. Nothing to uninstall."
        exit 0
      fi
    else
      SELECTED_TOOLS=("$tool")
    fi
    header "The Agency -- Uninstalling agents"
    local uninstalled=0
    for t in "${SELECTED_TOOLS[@]}"; do
      uninstall_tool "$t"
      (( uninstalled++ )) || true
    done
    printf "\n"
    ok "Uninstalled from $uninstalled tool(s)."
    exit 0
  fi

  # Decide whether to show interactive UI
  local use_interactive=false
  if   [[ "$interactive_mode" == "yes" ]]; then
    use_interactive=true
  elif [[ "$interactive_mode" == "auto" && -t 0 && -t 1 && "$tool" == "all" ]]; then
    use_interactive=true
  fi

  SELECTED_TOOLS=()

  if $use_interactive && interactive_wizard; then
    : # wizard committed SELECTED_TOOLS + FILTER_DIVISIONS

  elif [[ "$tool" != "all" ]]; then
    SELECTED_TOOLS=("$tool")

  else
    # Non-interactive (or no TTY): auto-detect
    header "The Agency -- Scanning for installed tools..."
    printf "\n"
    local t
    for t in "${ALL_TOOLS[@]}"; do
      if is_detected "$t" 2>/dev/null; then
        SELECTED_TOOLS+=("$t")
        printf "  ${C_GREEN}[*]${C_RESET}  %s  ${C_DIM}detected${C_RESET}\n" "$(tool_label "$t")"
      else
        printf "  ${C_DIM}[ ]  %s  not found${C_RESET}\n" "$(tool_label "$t")"
      fi
    done
  fi

  if [[ ${#SELECTED_TOOLS[@]} -eq 0 ]]; then
    warn "No tools selected or detected. Nothing to install."
    printf "\n"
    dim "  Tip: use --tool <name> to force-install a specific tool."
    dim "  Available: ${ALL_TOOLS[*]}"
    exit 0
  fi

  # --dry-run: print the plan and exit without writing anything.
  if $DRY_RUN; then
    local agents; agents="$(selected_agent_count)"
    printf "\n"; header "The Agency -- Dry run (nothing written)"
    printf "  Tools:   %s\n" "${SELECTED_TOOLS[*]}"
    if $SELECTION_ACTIVE; then
      [[ ${#FILTER_DIVISIONS[@]} -gt 0 ]] && printf "  Teams:   %s\n" "${FILTER_DIVISIONS[*]}"
      [[ ${#FILTER_AGENTS[@]} -gt 0 ]]    && printf "  Agents:  %s\n" "${FILTER_AGENTS[*]}"
      [[ -n "$AGENTS_FILE" ]]             && printf "  File:    %s\n" "$AGENTS_FILE"
    else
      printf "  Teams:   all (%s)\n" "${#ALL_DIVISIONS[@]}"
    fi
    printf "  Agents:  %s   Mode: %s\n" "$agents" "$($USE_LINK && echo symlink || echo copy)"
    local _t _cap
    for _t in "${SELECTED_TOOLS[@]}"; do
      _cap="$(tool_cap "$_t")"
      [[ "$_cap" -gt 0 && "$agents" -gt "$_cap" ]] && \
        warn "$_t caps ~$_cap -- ~$(( agents - _cap )) of $agents won't register (anomalyco/opencode#27988)"
    done
    printf "\n"; exit 0
  fi

  # When parent runs install.sh --parallel, it spawns workers with AGENCY_INSTALL_WORKER=1
  # so each worker only runs install_tool(s) and skips header/done box (avoids duplicate output).
  if [[ -n "${AGENCY_INSTALL_WORKER:-}" ]]; then
    local t
    for t in "${SELECTED_TOOLS[@]}"; do
      install_tool "$t"
    done
    return 0
  fi

  printf "\n"
  header "The Agency -- Installing agents"
  printf "  Repo:       %s\n" "$REPO_ROOT"
  local n_selected=${#SELECTED_TOOLS[@]}
  printf "  Installing: %s\n" "${SELECTED_TOOLS[*]}"
  if $SELECTION_ACTIVE; then
    [[ ${#FILTER_DIVISIONS[@]} -gt 0 ]] && printf "  Teams:      %s\n" "${FILTER_DIVISIONS[*]}"
    printf "  Agents:     %s of %s\n" "$(selected_agent_count)" "$(selected_agent_count_all)"
  fi
  $USE_LINK && printf "  Mode:       ${C_CYAN}symlink${C_RESET} (--link)\n"
  if $use_parallel; then
    ok "Installing $n_selected tools in parallel (output buffered per tool)."
  fi
  printf "\n"

  local installed=0 t i=0
  if $use_parallel; then
    local install_out_dir
    install_out_dir="$(mktemp -d)"
    export AGENCY_INSTALL_OUT_DIR="$install_out_dir"
    export AGENCY_INSTALL_SCRIPT="$SCRIPT_DIR/install.sh"
    export AGENCY_INSTALL_EXTRA="$(worker_flags)"
    printf '%s\n' "${SELECTED_TOOLS[@]}" | xargs -P "$parallel_jobs" -I {} sh -c 'AGENCY_INSTALL_WORKER=1 "$AGENCY_INSTALL_SCRIPT" --tool "{}" --no-interactive $AGENCY_INSTALL_EXTRA > "$AGENCY_INSTALL_OUT_DIR/{}" 2>&1'
    for t in "${SELECTED_TOOLS[@]}"; do
      [[ -f "$install_out_dir/$t" ]] && cat "$install_out_dir/$t"
    done
    rm -rf "$install_out_dir"
    installed=$n_selected
  else
    for t in "${SELECTED_TOOLS[@]}"; do
      (( i++ )) || true
      progress_bar "$i" "$n_selected"
      printf "\n"
      printf "  ${C_DIM}[%s/%s]${C_RESET} %s\n" "$i" "$n_selected" "$t"
      install_tool "$t"
      (( installed++ )) || true
    done
  fi

  # Dependency warning (after install, before done box)
  if $warn_deps; then
    warn_missing_deps
  fi

  # Post-install verification
  if $verify_mode; then
    verify_install
  fi

  # Done box
  local msg="  Done!  Installed $installed tool(s)."
  printf "\n"
  box_top
  box_row "${C_GREEN}${C_BOLD}${msg}${C_RESET}"
  box_bot
  printf "\n"
  dim "  Run ./scripts/convert.sh to regenerate after adding or editing agents."
  printf "\n"
}

main "$@"
