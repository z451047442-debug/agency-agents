#!/usr/bin/env bash
#
# lib.sh — Shared infrastructure for install.sh and per-tool install modules.
#
# This file is sourced (not executed). It provides:
#   1. Colour / output helpers
#   2. Progress bar + box drawing
#   3. Path resolution (SCRIPT_DIR, REPO_ROOT, INTEGRATIONS)
#   4. Agent directory discovery + selection engine
#   5. Install mechanics (copy, symlink, path override)
#   6. Tool detection
#   7. Interactive wizard (pure-bash TUI)
#   8. Generic uninstall / list-installed / verify-install
#   9. Per-tool dispatch (install_tool, uninstall_tool)
#
# Per-tool install/uninstall functions are defined in separate modules under
# scripts/install/ and are sourced by install.sh after this file.

# ---------------------------------------------------------------------------
# Guard against double-inclusion
# ---------------------------------------------------------------------------
[[ -n "${_AGENCY_INSTALL_LIB_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_LIB_GUARD=1

# ---------------------------------------------------------------------------
# Colours -- only when stdout supports color
# ---------------------------------------------------------------------------
if [[ -t 1 && -z "${NO_COLOR:-}" && "${TERM:-}" != "dumb" ]]; then
  C_GREEN=$'\033[0;32m'
  C_YELLOW=$'\033[1;33m'
  C_RED=$'\033[0;31m'
  C_CYAN=$'\033[0;36m'
  C_BOLD=$'\033[1m'
  C_DIM=$'\033[2m'
  C_RESET=$'\033[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_CYAN=''; C_BOLD=''; C_DIM=''; C_RESET=''
fi

ok()     { printf "${C_GREEN}[OK]${C_RESET}  %s\n" "$*"; }
warn()   { printf "${C_YELLOW}[!!]${C_RESET}  %s\n" "$*"; }
err()    { printf "${C_RED}[ERR]${C_RESET} %s\n" "$*" >&2; }
header() { printf "\n${C_BOLD}%s${C_RESET}\n" "$*"; }
dim()    { printf "${C_DIM}%s${C_RESET}\n" "$*"; }
info()   { printf "[..]  %s\n" "$*"; }

# Progress bar: [=======>    ] 3/8 (tqdm-style)
progress_bar() {
  local current="$1" total="$2" width="${3:-20}" i filled empty
  (( total > 0 )) || return
  filled=$(( width * current / total ))
  empty=$(( width - filled ))
  printf "\r  ["
  for (( i=0; i<filled; i++ )); do printf "="; done
  if (( filled < width )); then printf ">"; (( empty-- )); fi
  for (( i=0; i<empty; i++ )); do printf " "; done
  printf "] %s/%s" "$current" "$total"
  [[ -t 1 ]] || printf "\n"
}

# ---------------------------------------------------------------------------
# Box drawing -- pure ASCII, fixed 52-char wide
#   box_top / box_sep / box_bot -- structural lines
#   box_row <text>             -- content row, right-padded to fit
# ---------------------------------------------------------------------------
BOX_INNER=48   # chars between the two | walls

box_top() { printf "  +"; printf '%0.s-' $(seq 1 $BOX_INNER); printf "+\n"; }
box_bot() { box_top; }
box_sep() { printf "  |"; printf '%0.s-' $(seq 1 $BOX_INNER); printf "|\n"; }
strip_ansi() {
  awk '{ gsub(/\033\[[0-9;]*m/, ""); print }' <<< "$1"
}
box_row() {
  # Strip ANSI escapes when measuring visible length
  local raw="$1"
  local visible
  visible="$(strip_ansi "$raw")"
  local pad=$(( BOX_INNER - 2 - ${#visible} ))
  if (( pad < 0 )); then pad=0; fi
  printf "  | %s%*s |\n" "$raw" "$pad" ''
}
box_blank() { printf "  |%*s|\n" $BOX_INNER ''; }

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# _AGENCY_INSTALL_LIB_DIR = scripts/install/
_AGENCY_INSTALL_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# SCRIPT_DIR = scripts/
SCRIPT_DIR="$(cd "$_AGENCY_INSTALL_LIB_DIR/.." && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
INTEGRATIONS="$REPO_ROOT/integrations"

# Shared helpers (get_field, agent_slug, slugify, incr, ANSI + TUI primitives)
# shellcheck source=../lib.sh
. "$SCRIPT_DIR/lib.sh"

ALL_TOOLS=(claude-code copilot antigravity gemini-cli opencode openclaw cursor aider windsurf qwen kimi codex osaurus hermes)

# Auto-discover all agent category directories (shared logic -- see _discover_dirs.sh)
source "$SCRIPT_DIR/_discover_dirs.sh"
AGENT_DIRS=()
while IFS= read -r d; do
  AGENT_DIRS+=("$d")
done < <(discover_agent_dirs)

# ---------------------------------------------------------------------------
# Selection engine (team / agent / agents-file filtering)
# ---------------------------------------------------------------------------
# Selectable divisions = AGENT_DIRS minus strategy/ (NEXUS docs, not agents).
ALL_DIVISIONS=(
  academic design engineering finance game-development gis marketing paid-media
  product project-management sales security spatial-computing specialized support testing
)

FILTER_DIVISIONS=()      # --division
FILTER_AGENTS=()         # --agent
AGENTS_FILE=""           # --agents-file
DRY_RUN=false            # --dry-run
SELECTION_ACTIVE=false   # true once any agent-level filter is applied
_ALLOWED_SLUGS=""        # newline-delimited cache of allowed slugs

# division_files <division> -- agent file paths (frontmatter only) in a division.
division_files() {
  local d="$REPO_ROOT/$1" f
  [[ -d "$d" ]] || return 0
  while IFS= read -r -d '' f; do
    is_agent_file "$f" && printf '%s\n' "$f"
  done < <(find "$d" -name "*.md" -type f -print0 2>/dev/null)
}

# division_count <division> -- number of agents in a division.
division_count() { division_files "$1" | grep -c . ; }

# build_selection -- compute the allowed slug set from --division/--agent/--agents-file.
# With no filter flags, SELECTION_ACTIVE stays false (install everything).
build_selection() {
  if [[ ${#FILTER_DIVISIONS[@]} -eq 0 && ${#FILTER_AGENTS[@]} -eq 0 && -z "$AGENTS_FILE" ]]; then
    SELECTION_ACTIVE=false
    return
  fi
  SELECTION_ACTIVE=true
  local slugs="" div f s line
  for div in ${FILTER_DIVISIONS[@]+"${FILTER_DIVISIONS[@]}"}; do
    while IFS= read -r f; do
      s="$(agent_slug "$f")"; [[ -n "$s" ]] && slugs+="$s"$'\n'
    done < <(division_files "$div")
  done
  for s in ${FILTER_AGENTS[@]+"${FILTER_AGENTS[@]}"}; do slugs+="$(slugify "$s")"$'\n'; done
  if [[ -n "$AGENTS_FILE" ]]; then
    [[ -f "$AGENTS_FILE" ]] || { err "agents-file not found: $AGENTS_FILE"; exit 1; }
    while IFS= read -r line || [[ -n "$line" ]]; do
      line="${line%%#*}"                              # strip trailing comment
      line="$(printf '%s' "$line" | xargs 2>/dev/null)" # trim
      [[ -z "$line" ]] && continue
      slugs+="$(slugify "$line")"$'\n'
    done < "$AGENTS_FILE"
  fi
  _ALLOWED_SLUGS="$(printf '%s' "$slugs" | sort -u | sed '/^$/d')"
}

# slug_allowed <slug> -- true if installable under the active selection
# (always true when no filter). Tolerates the antigravity "agency-" prefix.
slug_allowed() {
  $SELECTION_ACTIVE || return 0
  local s="${1#agency-}"
  printf '%s\n' "$_ALLOWED_SLUGS" | grep -qxF "$s"
}

# selected_agent_count -- how many agents the current selection installs.
selected_agent_count() {
  if ! $SELECTION_ACTIVE; then
    local d n=0; for d in "${ALL_DIVISIONS[@]}"; do incr_by n "$(division_count "$d")"; done; echo "$n"
  else
    printf '%s\n' "$_ALLOWED_SLUGS" | grep -c .
  fi
}
incr_by() { printf -v "$1" '%d' "$(( ${!1:-0} + ${2:-0} ))"; }

# selected_agent_count_all -- total agents across all divisions (ignores filter).
selected_agent_count_all() {
  local d n=0; for d in "${ALL_DIVISIONS[@]}"; do incr_by n "$(division_count "$d")"; done; echo "$n"
}

# worker_flags -- re-emit the active selection/mode flags for parallel workers.
worker_flags() {
  local out="" d a
  $USE_LINK && out="$out --link"
  $AUTO_CONVERT || out="$out --no-convert"
  [[ -n "$OVERRIDE_PATH" ]] && out="$out --path $OVERRIDE_PATH"
  for d in ${FILTER_DIVISIONS[@]+"${FILTER_DIVISIONS[@]}"}; do out="$out --division $d"; done
  for a in ${FILTER_AGENTS[@]+"${FILTER_AGENTS[@]}"}; do out="$out --agent $a"; done
  [[ -n "$AGENTS_FILE" ]] && out="$out --agents-file $AGENTS_FILE"
  printf '%s' "$out"
}

# validate_division <name> -- exit on unknown division.
validate_division() {
  local _ad
  for _ad in "${ALL_DIVISIONS[@]}"; do [[ "$_ad" == "$1" ]] && return 0; done
  err "Unknown division '$1'. Valid: ${ALL_DIVISIONS[*]}"
  exit 1
}

# ---------------------------------------------------------------------------
# Install mechanics (copy vs symlink, path override, capacity guard)
# ---------------------------------------------------------------------------
USE_LINK=false        # --link
OVERRIDE_PATH=""      # --path (single-destination override)

# install_file <src> <dest> -- copy, or symlink when --link is set.
install_file() {
  if $USE_LINK; then ln -sf "$1" "$2"; else cp "$1" "$2"; fi
}

# resolve_dest <tool> <default> -- --path > $ENV_VAR > default.
resolve_dest() {
  local tool="$1" def="$2" var=""
  [[ -n "$OVERRIDE_PATH" ]] && { printf '%s' "$OVERRIDE_PATH"; return; }
  case "$tool" in
    claude-code) var="CLAUDE_CONFIG_DIR" ;;
    copilot)     var="COPILOT_AGENT_DIR" ;;
    cursor)      var="CURSOR_RULES_DIR" ;;
    gemini-cli)  var="GEMINI_AGENTS_DIR" ;;
    opencode)    var="OPENCODE_AGENTS_DIR" ;;
    openclaw)    var="OPENCLAW_DIR" ;;
    qwen)        var="QWEN_AGENTS_DIR" ;;
    codex)       var="CODEX_AGENTS_DIR" ;;
    osaurus)     var="OSAURUS_SKILLS_DIR" ;;
    hermes)      var="HERMES_PLUGIN_DIR" ;;
  esac
  if [[ -n "$var" && -n "${!var:-}" ]]; then printf '%s' "${!var}"; else printf '%s' "$def"; fi
}

# resolve_tool_path <tool> -- best-effort binary path for the detection UI.
resolve_tool_path() {
  local bin=""
  case "$1" in
    claude-code) bin="claude" ;; copilot) bin="code" ;; gemini-cli) bin="gemini" ;;
    opencode) bin="opencode" ;; openclaw) bin="openclaw" ;; cursor) bin="cursor" ;;
    aider) bin="aider" ;; windsurf) bin="windsurf" ;; qwen) bin="qwen" ;;
    kimi) bin="kimi" ;; codex) bin="codex" ;; antigravity) bin="" ;;
    osaurus) bin="osaurus" ;; hermes) bin="hermes" ;;
  esac
  [[ -n "$bin" ]] && command -v "$bin" 2>/dev/null
}

# hermes_home_dir -- home directory for Hermes configuration.
hermes_home_dir() { echo "${HERMES_HOME:-${HOME}/.hermes}"; }

# ensure_converted <tool> -- auto-run convert.sh if a converted tool's output
# is missing (absorbs #426). No-op for source tools and when --no-convert.
ensure_converted() {
  local tool="$1"
  $AUTO_CONVERT || return 0
  case "$tool" in claude-code|copilot) return 0 ;; esac
  local d="$INTEGRATIONS/$tool"
  if [[ ! -d "$d" ]] || [[ -z "$(find "$d" -type f 2>/dev/null | head -1)" ]]; then
    warn "$tool: integration files missing -- running convert.sh --tool $tool"
    "$SCRIPT_DIR/convert.sh" --tool "$tool" >/dev/null 2>&1 \
      && ok "$tool: generated integration files" \
      || err "$tool: convert.sh failed; run it manually"
  fi
}
AUTO_CONVERT=true     # --no-convert disables

# Per-tool soft capacity (opencode silently drops past ~119 -- upstream #27988).
tool_cap() { case "$1" in opencode) echo 119 ;; *) echo 0 ;; esac; }

# capacity_warn <tool> <count> -- warn if a tool can't register this many.
capacity_warn() {
  local cap; cap="$(tool_cap "$1")"
  if [[ "$cap" -gt 0 && "$2" -gt "$cap" ]]; then
    warn "$1: registers only ~$cap agents (upstream bug anomalyco/opencode#27988)."
    warn "      You selected $2 -- ~$(( $2 - cap )) won't load. Narrow with --division to fix."
  fi
}

# do_list <what> -- print tools/teams/agents and exit.
do_list() {
  case "$1" in
    tools)
      printf '%s\n' "${ALL_TOOLS[@]}" ;;
    teams|divisions)
      local d; for d in "${ALL_DIVISIONS[@]}"; do printf '%-22s %3s agents\n' "$d" "$(division_count "$d")"; done ;;
    agents)
      local d f; for d in "${ALL_DIVISIONS[@]}"; do
        while IFS= read -r f; do printf '%-20s %s\n' "$d" "$(agent_slug "$f")"; done < <(division_files "$d")
      done ;;
    *)
      echo "Tools (${#ALL_TOOLS[@]}):"; printf '  %s\n' "${ALL_TOOLS[@]}"; echo
      echo "Teams (${#ALL_DIVISIONS[@]}):"
      local d; for d in "${ALL_DIVISIONS[@]}"; do printf '  %-22s %3s agents\n' "$d" "$(division_count "$d")"; done ;;
  esac
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
check_integrations() {
  if [[ ! -d "$INTEGRATIONS" ]]; then
    err "integrations/ not found. Run ./scripts/convert.sh first."
    exit 1
  fi
}

# ---------------------------------------------------------------------------
# Tool detection
# ---------------------------------------------------------------------------
detect_claude_code() { [[ -d "${HOME}/.claude" ]]; }
detect_copilot()      { command -v code >/dev/null 2>&1 || [[ -d "${HOME}/.github" || -d "${HOME}/.copilot" ]]; }
detect_antigravity()  { [[ -d "${HOME}/.gemini/antigravity/skills" ]]; }
detect_gemini_cli()   { command -v gemini >/dev/null 2>&1 || [[ -d "${HOME}/.gemini" ]]; }
detect_cursor()       { command -v cursor >/dev/null 2>&1 || [[ -d "${HOME}/.cursor" ]]; }
detect_opencode()     { command -v opencode >/dev/null 2>&1 || [[ -d "${HOME}/.config/opencode" ]]; }
detect_aider()        { command -v aider >/dev/null 2>&1; }
detect_openclaw()     { command -v openclaw >/dev/null 2>&1 || [[ -d "${HOME}/.openclaw" ]]; }
detect_windsurf()     { command -v windsurf >/dev/null 2>&1 || [[ -d "${HOME}/.codeium" ]]; }
detect_qwen()         { command -v qwen >/dev/null 2>&1 || [[ -d "${HOME}/.qwen" ]]; }
detect_kimi()         { command -v kimi >/dev/null 2>&1; }
detect_codex()        { command -v codex >/dev/null 2>&1 || [[ -d "${HOME}/.codex" ]]; }
detect_osaurus()      { command -v osaurus >/dev/null 2>&1 || [[ -d "${HOME}/.osaurus" ]]; }
detect_hermes()       { command -v hermes >/dev/null 2>&1 || [[ -d "${HERMES_HOME:-${HOME}/.hermes}" ]]; }

is_detected() {
  case "$1" in
    claude-code) detect_claude_code ;;
    copilot)     detect_copilot     ;;
    antigravity) detect_antigravity ;;
    gemini-cli)  detect_gemini_cli  ;;
    opencode)    detect_opencode    ;;
    openclaw)    detect_openclaw    ;;
    cursor)      detect_cursor      ;;
    aider)       detect_aider       ;;
    windsurf)    detect_windsurf    ;;
    qwen)        detect_qwen        ;;
    kimi)        detect_kimi        ;;
    codex)       detect_codex       ;;
    osaurus)     detect_osaurus     ;;
    hermes)      detect_hermes      ;;
    *)           return 1 ;;
  esac
}

# Fixed-width labels: name (14) + detail (24) = 38 visible chars
tool_label() {
  case "$1" in
    claude-code) printf "%-14s  %s" "Claude Code"  "(claude.ai/code)"        ;;
    copilot)     printf "%-14s  %s" "Copilot"      "(~/.github + ~/.copilot)" ;;
    antigravity) printf "%-14s  %s" "Antigravity"  "(~/.gemini/antigravity)" ;;
    gemini-cli)  printf "%-14s  %s" "Gemini CLI"   "(~/.gemini/agents)"      ;;
    opencode)    printf "%-14s  %s" "OpenCode"     "(opencode.ai)"           ;;
    openclaw)    printf "%-14s  %s" "OpenClaw"     "(~/.openclaw/agency-agents)" ;;
    cursor)      printf "%-14s  %s" "Cursor"       "(.cursor/rules)"         ;;
    aider)       printf "%-14s  %s" "Aider"        "(CONVENTIONS.md)"        ;;
    windsurf)    printf "%-14s  %s" "Windsurf"     "(.windsurfrules)"        ;;
    qwen)        printf "%-14s  %s" "Qwen Code"    "(~/.qwen/agents)"        ;;
    kimi)        printf "%-14s  %s" "Kimi Code"    "(~/.config/kimi/agents)" ;;
    codex)       printf "%-14s  %s" "Codex"        "(~/.codex/agents)"       ;;
    osaurus)     printf "%-14s  %s" "Osaurus"      "(~/.osaurus/skills)"     ;;
    hermes)      printf "%-14s  %s" "Hermes"       "(~/.hermes/plugins)"     ;;
  esac
}

tool_simple_name() {
  case "$1" in
    claude-code) echo "Claude Code";; copilot) echo "Copilot";; antigravity) echo "Antigravity";;
    gemini-cli) echo "Gemini CLI";; opencode) echo "OpenCode";; openclaw) echo "OpenClaw";;
    cursor) echo "Cursor";; aider) echo "Aider";; windsurf) echo "Windsurf";;
    qwen) echo "Qwen Code";; kimi) echo "Kimi Code";; codex) echo "Codex";; osaurus) echo "Osaurus";;
    hermes) echo "Hermes";; *) echo "$1";;
  esac
}

# ---------------------------------------------------------------------------
# Interactive selector
# ---------------------------------------------------------------------------
# Interactive wizard (pure-bash TUI):  Tools -> Teams -> Review -> install
# Uses lib.sh primitives (tui_begin/read_key/draw_frame). Falls back to the
# legacy auto-detect path when there is no TTY.

# Persistent selection state across screens.
TOOL_SEL=()      # 1/0 per ALL_TOOLS
TEAM_SEL=()      # 1/0 per ALL_DIVISIONS

# division_emoji <div> -- a glyph for the team list (unicode only).
division_emoji() {
  if ! supports_unicode; then printf '*'; return; fi
  case "$1" in
    academic) printf '📚';; design) printf '🎨';; engineering) printf '💻';;
    finance) printf '💵';; game-development) printf '🎮';; gis) printf '🌍';; marketing) printf '📢';;
    paid-media) printf '💰';; product) printf '📊';; project-management) printf '🎬';;
    sales) printf '💼';; security) printf '🔒';; spatial-computing) printf '🥽';;
    specialized) printf '🎯';; support) printf '🛟';; testing) printf '🧪';; *) printf '•';;
  esac
}

# Generic multi-select. Inputs (globals): OPT_LABEL[], OPT_SEL[];
# SEL_TITLE, SEL_HINT, SEL_SUMMARY_FN, SEL_NAV, SEL_WARN_FN.
# Mutates OPT_SEL[]; sets SEL_RESULT = next|back|quit.
selector() {
  local n=${#OPT_LABEL[@]} cur=0 top=0 query="" searching=false key i idx vn rows W
  rows=$(( $(term_rows) - 9 )); (( rows < 3 )) && rows=3
  while true; do
    local view=() qlc
    qlc="$(printf '%s' "$query" | tr '[:upper:]' '[:lower:]')"
    for (( i=0; i<n; i++ )); do
      if [[ -z "$query" || "$(printf '%s' "${OPT_LABEL[$i]}" | tr '[:upper:]' '[:lower:]')" == *"$qlc"* ]]; then
        view+=("$i")
      fi
    done
    vn=${#view[@]}
    (( cur>=vn )) && cur=$(( vn>0 ? vn-1 : 0 ))
    (( cur<top )) && top=$cur
    (( cur>=top+rows )) && top=$(( cur-rows+1 ))
    W=$(( $(term_cols) - 4 )); (( W>74 )) && W=74; (( W<40 )) && W=40
    local buf="" hlen=$(( W - ${#SEL_TITLE} - 5 )); (( hlen<1 )) && hlen=1
    buf+="  ${C_BOLD}${C_CYAN}${BX_TL}${BX_H}${BX_H} ${SEL_TITLE} $(repeat "$BX_H" "$hlen")${BX_TR}${C_RESET}"$'\n'
    buf+="  ${C_DIM}${SEL_HINT}${C_RESET}"$'\n\n'
    (( vn==0 )) && buf+="   ${C_DIM}(no matches)${C_RESET}"$'\n'
    for (( i=top; i<top+rows && i<vn; i++ )); do
      idx=${view[$i]}
      local mark cg label="${OPT_LABEL[$idx]}"
      [[ "${OPT_SEL[$idx]}" == 1 ]] && mark="${C_GREEN}${GLYPH_ON}${C_RESET}" || mark="${C_DIM}·${C_RESET}"
      if (( i==cur )); then cg="${C_CYAN}${GLYPH_CUR}${C_RESET}"; label="${C_BOLD}${label}${C_RESET}"; else cg=" "; fi
      buf+="   $cg [$mark] $label"$'\n'
    done
    local shown=$(( vn<rows ? vn : rows )); for (( i=shown; i<rows; i++ )); do buf+=$'\n'; done
    # Consistent footer: summary -> nav -> warnings (-> search line)
    buf+=$'\n'"  ${C_BOLD}$("$SEL_SUMMARY_FN")${C_RESET}"$'\n'
    buf+="  ${C_DIM}${SEL_NAV}${C_RESET}"$'\n'
    local _w; _w="$("$SEL_WARN_FN")"; [[ -n "$_w" ]] && buf+="  ${C_YELLOW}${_w}${C_RESET}"$'\n'
    if $searching; then buf+="  ${C_CYAN}search:${C_RESET} ${query}_"$'\n'
    elif [[ -n "$query" ]]; then buf+="  ${C_CYAN}/${query}${C_RESET}  ${C_DIM}(esc clears)${C_RESET}"$'\n'; fi
    draw_frame "$buf"

    key="$(read_key)"
    if $searching; then
      case "$key" in
        ENTER) searching=false ;;
        ESC)   query=""; searching=false ;;
        BACKSPACE) query="${query%?}" ;;
        *) [[ ${#key} -eq 1 ]] && query="$query$key" ;;
      esac
      continue
    fi
    case "$key" in
      UP|k)        (( cur>0 ))    && cur=$(( cur-1 )) ;;
      DOWN|j)      (( cur<vn-1 )) && cur=$(( cur+1 )) ;;
      SPACE)       (( vn>0 )) && { idx=${view[$cur]}; OPT_SEL[$idx]=$(( 1 - ${OPT_SEL[$idx]} )); } ;;
      a|A)         for (( i=0; i<n; i++ )); do OPT_SEL[$i]=1; done ;;
      n|N)         for (( i=0; i<n; i++ )); do OPT_SEL[$i]=0; done ;;
      /)           searching=true ;;
      ENTER|RIGHT) SEL_RESULT=next; return ;;
      LEFT)        SEL_RESULT=back; return ;;
      ESC)         [[ -n "$query" ]] && query="" || { SEL_RESULT=back; return; } ;;
      q|Q)         SEL_RESULT=quit; return ;;
      EOF)         SEL_RESULT=quit; return ;;
    esac
  done
}

# --- Screen: Tools ---
_no_warn() { :; }
_tools_summary() {
  local i c=0; for (( i=0; i<${#OPT_SEL[@]}; i++ )); do [[ "${OPT_SEL[$i]}" == 1 ]] && c=$(( c+1 )); done
  printf '%s of %s tools selected' "$c" "${#OPT_SEL[@]}"
}
screen_tools() {
  OPT_LABEL=(); OPT_SEL=()
  local i det path label
  for (( i=0; i<${#ALL_TOOLS[@]}; i++ )); do
    local t="${ALL_TOOLS[$i]}"
    path="$(resolve_tool_path "$t" 2>/dev/null || true)"
    if is_detected "$t" 2>/dev/null; then det="${C_GREEN}${GLYPH_DET}${C_RESET}"; else det="${C_DIM}${GLYPH_OFF}${C_RESET}"; fi
    label="$(printf '%s %-13s %s' "$det" "$(tool_simple_name "$t")" "${C_DIM}${path:-not found}${C_RESET}")"
    OPT_LABEL+=("$label"); OPT_SEL+=("${TOOL_SEL[$i]:-0}")
  done
  SEL_TITLE="The Agency · Installer  --  1/3 · Tools"
  SEL_HINT="Pick where to install.  ${GLYPH_DET} = detected on this machine."
  SEL_SUMMARY_FN=_tools_summary
  SEL_NAV="space toggle · a all · n none · / search · enter next · q quit"
  SEL_WARN_FN=_no_warn
  selector
  for (( i=0; i<${#OPT_SEL[@]}; i++ )); do TOOL_SEL[$i]="${OPT_SEL[$i]}"; done
}

# --- Screen: Teams ---
_teams_agents() {
  local i c=0 d
  for (( i=0; i<${#ALL_DIVISIONS[@]}; i++ )); do
    [[ "${OPT_SEL[$i]}" == 1 ]] && { d="${ALL_DIVISIONS[$i]}"; c=$(( c + ${TEAM_COUNTS[$i]} )); }
  done
  echo "$c"
}
_teams_summary() {
  local sel=0 i a; a="$(_teams_agents)"
  for (( i=0; i<${#OPT_SEL[@]}; i++ )); do [[ "${OPT_SEL[$i]}" == 1 ]] && sel=$(( sel+1 )); done
  printf '%s agents · %s of %s teams' "$a" "$sel" "${#OPT_SEL[@]}"
}
_teams_warn() {
  local a cap; a="$(_teams_agents)"; cap="$(tool_cap opencode)"
  if _opencode_selected && [[ "$a" -gt "$cap" ]]; then
    printf "⚠ OpenCode registers ~%s; ~%s of %s won't load (#27988)" "$cap" "$(( a - cap ))" "$a"
  fi
}
_opencode_selected() {
  local i; for (( i=0; i<${#TOOL_SEL[@]}; i++ )); do
    [[ "${ALL_TOOLS[$i]}" == "opencode" && "${TOOL_SEL[$i]}" == 1 ]] && return 0
  done; return 1
}
screen_teams() {
  OPT_LABEL=(); OPT_SEL=()
  local i
  for (( i=0; i<${#ALL_DIVISIONS[@]}; i++ )); do
    local d="${ALL_DIVISIONS[$i]}"
    OPT_LABEL+=("$(printf '%s %-20s %s' "$(division_emoji "$d")" "$d" "${C_DIM}${TEAM_COUNTS[$i]} agents${C_RESET}")")
    OPT_SEL+=("${TEAM_SEL[$i]:-1}")
  done
  SEL_TITLE="The Agency · Installer  --  2/3 · Teams"
  SEL_HINT="Pick which teams to install.  Fewer teams keeps OpenCode under its limit."
  SEL_SUMMARY_FN=_teams_summary
  SEL_NAV="space toggle · a all · n none · / search · enter next · ← back · q quit"
  SEL_WARN_FN=_teams_warn
  selector
  for (( i=0; i<${#OPT_SEL[@]}; i++ )); do TEAM_SEL[$i]="${OPT_SEL[$i]}"; done
}

# --- Screen: Review ---
REVIEW_RESULT=""
# grid_2col <cellwidth> <items...> -- lay items out in two column-major columns
# (left column filled top-to-bottom first). Plain text cells (no ANSI) so the
# width padding stays correct.
grid_2col() {
  local w="$1"; shift
  local n=$# r rows left right out=""
  (( n==0 )) && { printf '     %snone%s\n' "$C_DIM" "$C_RESET"; return; }
  local items=("$@")
  rows=$(( (n + 1) / 2 ))
  for (( r=0; r<rows; r++ )); do
    left="${items[$r]}"
    right="${items[$(( r + rows ))]:-}"
    if [[ -n "$right" ]]; then out+="$(printf '     %-*s  %s' "$w" "$left" "$right")"$'\n'
    else out+="     $left"$'\n'; fi
  done
  printf '%s' "$out"
}

screen_review() {
  local tools=() teams=() i agents
  for (( i=0; i<${#TOOL_SEL[@]}; i++ )); do [[ "${TOOL_SEL[$i]}" == 1 ]] && tools+=("$(tool_simple_name "${ALL_TOOLS[$i]}")"); done
  for (( i=0; i<${#TEAM_SEL[@]}; i++ )); do [[ "${TEAM_SEL[$i]}" == 1 ]] && teams+=("${ALL_DIVISIONS[$i]}"); done
  agents=0; for (( i=0; i<${#TEAM_SEL[@]}; i++ )); do [[ "${TEAM_SEL[$i]}" == 1 ]] && agents=$(( agents + ${TEAM_COUNTS[$i]} )); done
  local cur=0   # 0=Install 1=mode toggle
  while true; do
    local buf="" m
    # pager
    buf+="  ${C_BOLD}${C_CYAN}${BX_TL}${BX_H}${BX_H} The Agency · Installer  --  3/3 · Review $(repeat "$BX_H" 28)${BX_TR}${C_RESET}"$'\n'
    # description
    buf+="  ${C_DIM}Confirm your selection, then install.${C_RESET}"$'\n\n'
    # content: the selections + the mode toggle
    buf+="   ${C_BOLD}Tools${C_RESET} ${C_DIM}(${#tools[@]})${C_RESET}"$'\n'
    buf+="$(grid_2col 16 ${tools[@]+"${tools[@]}"})"$'\n'
    buf+="   ${C_BOLD}Teams${C_RESET} ${C_DIM}(${#teams[@]})${C_RESET}"$'\n'
    buf+="$(grid_2col 20 ${teams[@]+"${teams[@]}"})"$'\n\n'
    $USE_LINK && m="symlink" || m="copy"
    if (( cur==1 )); then buf+="   ${C_CYAN}${GLYPH_CUR}${C_RESET} Mode: ${C_BOLD}${m}${C_RESET}  ${C_DIM}(space toggles copy/symlink)${C_RESET}"$'\n'
    else buf+="     Mode: ${m}  ${C_DIM}(space toggles copy/symlink)${C_RESET}"$'\n'; fi
    buf+=$'\n'
    # summary
    buf+="  ${C_BOLD}Installing ${agents} agents · ${#teams[@]} teams · ${#tools[@]} tools${C_RESET}"$'\n'
    # navigation (Install is the action cursor target)
    if (( cur==0 )); then buf+="  ${C_CYAN}${GLYPH_CUR}${C_RESET} ${C_BOLD}${C_GREEN}Install${C_RESET}   ${C_DIM}↑/↓ move · enter install · ← back · q quit${C_RESET}"$'\n'
    else buf+="    ${C_GREEN}Install${C_RESET}   ${C_DIM}↑/↓ move · space toggle mode · ← back · q quit${C_RESET}"$'\n'; fi
    # warnings
    local cap; cap="$(tool_cap opencode)"
    if printf '%s\n' "${tools[@]}" | grep -qx "OpenCode" && [[ "$agents" -gt "$cap" ]]; then
      buf+="  ${C_YELLOW}⚠ OpenCode registers ~${cap}; ~$(( agents - cap )) of ${agents} won't load (#27988)${C_RESET}"$'\n'
    fi
    draw_frame "$buf"
    local key; key="$(read_key)"
    case "$key" in
      UP|DOWN|k|j|TAB) cur=$(( 1 - cur )) ;;
      SPACE) (( cur==1 )) && { $USE_LINK && USE_LINK=false || USE_LINK=true; } ;;
      ENTER) if (( cur==0 )); then REVIEW_RESULT=install; return; fi ;;
      LEFT)  REVIEW_RESULT=back; return ;;
      q|Q|EOF) REVIEW_RESULT=quit; return ;;
    esac
  done
}

# interactive_wizard -- drive the three screens; commit to SELECTED_TOOLS /
# FILTER_DIVISIONS / USE_LINK. Returns 1 if no TTY (caller falls back).
interactive_wizard() {
  init_ansi
  TEAM_COUNTS=(); local i
  for (( i=0; i<${#ALL_DIVISIONS[@]}; i++ )); do TEAM_COUNTS+=("$(division_count "${ALL_DIVISIONS[$i]}")"); done
  # seed defaults: tools = detected, teams = all
  TOOL_SEL=(); for (( i=0; i<${#ALL_TOOLS[@]}; i++ )); do is_detected "${ALL_TOOLS[$i]}" 2>/dev/null && TOOL_SEL+=(1) || TOOL_SEL+=(0); done
  TEAM_SEL=(); for (( i=0; i<${#ALL_DIVISIONS[@]}; i++ )); do TEAM_SEL+=(1); done

  tui_begin || return 1
  local screen=tools
  while true; do
    case "$screen" in
      tools)  screen_tools;  case "$SEL_RESULT" in next) screen=teams;; quit) tui_end; exit 0;; esac ;;
      teams)  screen_teams;  case "$SEL_RESULT" in next) screen=review;; back) screen=tools;; quit) tui_end; exit 0;; esac ;;
      review) screen_review; case "$REVIEW_RESULT" in install) break;; back) screen=teams;; quit) tui_end; exit 0;; esac ;;
    esac
  done
  tui_end

  # commit
  SELECTED_TOOLS=()
  for (( i=0; i<${#TOOL_SEL[@]}; i++ )); do [[ "${TOOL_SEL[$i]}" == 1 ]] && SELECTED_TOOLS+=("${ALL_TOOLS[$i]}"); done
  FILTER_DIVISIONS=()
  local all=1
  for (( i=0; i<${#TEAM_SEL[@]}; i++ )); do [[ "${TEAM_SEL[$i]}" == 1 ]] || all=0; done
  if [[ "$all" == 0 ]]; then
    for (( i=0; i<${#TEAM_SEL[@]}; i++ )); do [[ "${TEAM_SEL[$i]}" == 1 ]] && FILTER_DIVISIONS+=("${ALL_DIVISIONS[$i]}"); done
  fi
  build_selection
  return 0
}

# ---------------------------------------------------------------------------
# Generic uninstall + tool-specific dispatch
# ---------------------------------------------------------------------------

# Global for single-agent uninstall (set by main() from --agent flag).
single_agent=""

uninstall_generic() {
  local label="$1" dest="$2" count=0
  [[ -d "$dest" ]] || { info "$label: nothing to uninstall"; return 0; }
  if [[ -n "$single_agent" ]]; then
    local target="${dest}/${single_agent}.md"
    # Some tools use subdirectories (e.g. antigravity: agency-frontend-developer/SKILL.md)
    if [[ -f "$target" ]]; then
      rm -f "$target" && (( count++ )) || true
    elif [[ -d "${dest}/${single_agent}" ]]; then
      rm -rf "${dest}/${single_agent}" && (( count++ )) || true
    else
      info "$label: agent '$single_agent' not installed"
      return 0
    fi
    ok "$label: removed $single_agent"
    return 0
  fi
  while IFS= read -r -d """" f; do
    [[ "$(head -1 "$f")" == "---" ]] || continue
    rm -f "$f" && (( count++ )) || true
  done < <(find "$dest" -name "*.md" -type f -print0 2>/dev/null)
  ok "$label: removed $count agents from $dest"
}

# uninstall_tool <tool> -- dispatched from main().
# Cases that need special handling reference functions from per-tool modules
# (sourced by install.sh after this file).
uninstall_tool() {
  local tool="$1"
  info "Uninstalling The Agency from: $(tool_label "$tool")"
  case "$tool" in
    claude-code) uninstall_claude_code ;;
    copilot)     uninstall_generic "Copilot" "${HOME}/.github/agents"; uninstall_generic "Copilot" "${HOME}/.copilot/agents" ;;
    antigravity) uninstall_generic "Antigravity" "${HOME}/.gemini/antigravity/skills" ;;
    gemini-cli)  uninstall_generic "Gemini CLI" "${HOME}/.gemini/extensions" ;;
    opencode)    uninstall_generic "OpenCode" "${HOME}/.config/opencode/agents" ;;
    openclaw)    uninstall_generic "OpenClaw" "${HOME}/.openclaw/agency-agents" ;;
    cursor)      uninstall_generic "Cursor" "${HOME}/.cursor/rules" ;;
    aider)       uninstall_generic "Aider" "${REPO_ROOT}" ;;
    windsurf)    uninstall_generic "Windsurf" "${REPO_ROOT}" ;;
    qwen)        uninstall_generic "Qwen Code" "${HOME}/.qwen/agents" ;;
    kimi)        uninstall_generic "Kimi Code" "${HOME}/.config/kimi/agents" ;;
    codex)       uninstall_generic "Codex" "${HOME}/.codex/agents" ;;
    osaurus)     uninstall_generic "Osaurus" "${HOME}/.osaurus/skills" ;;
    hermes)      uninstall_generic "Hermes" "$(hermes_home_dir)/plugins" ;;
    *)           err "Unknown tool: $tool"; return 1 ;;
  esac
}

# ---------------------------------------------------------------------------
# list_installed -- iterate all tools, count agent files
# ---------------------------------------------------------------------------
list_installed() {
  local found=0
  header "Installed Agents"
  for t in "${ALL_TOOLS[@]}"; do
    local dest label
    case "$t" in
      claude-code) dest="${HOME}/.claude/agents"; label="Claude Code" ;;
      copilot)     dest="${HOME}/.github/agents"; label="Copilot" ;;
      antigravity) dest="${HOME}/.gemini/antigravity/skills"; label="Antigravity" ;;
      gemini-cli)  dest="${HOME}/.gemini/extensions/agency-agents/skills"; label="Gemini CLI" ;;
      opencode)    dest="${HOME}/.config/opencode/agents"; label="OpenCode" ;;
      openclaw)    dest="${HOME}/.openclaw/agency-agents"; label="OpenClaw" ;;
      cursor)      dest="${HOME}/.cursor/rules"; label="Cursor" ;;
      aider)       dest="${REPO_ROOT}"; label="Aider (CONVENTIONS.md)" ;;
      windsurf)    dest="${REPO_ROOT}"; label="Windsurf (.windsurfrules)" ;;
      qwen)        dest="${HOME}/.qwen/agents"; label="Qwen Code" ;;
      kimi)        dest="${HOME}/.config/kimi/agents"; label="Kimi Code" ;;
      codex)       dest="${HOME}/.codex/agents"; label="Codex" ;;
      osaurus)     dest="${HOME}/.osaurus/skills"; label="Osaurus" ;;
      hermes)      dest="$(hermes_home_dir)/plugins"; label="Hermes" ;;
      *)           continue ;;
    esac
    if [[ -d "$dest" ]]; then
      local count
      count=$(find "$dest" -name "*.md" -type f 2>/dev/null | wc -l)
      if [[ "$count" -gt 0 ]]; then
        echo "  ${C_CYAN}${label}${C_RESET}: ${count} agents in ${dest}"
        found=$((found + count))
      fi
    fi
  done
  if [[ "$found" -eq 0 ]]; then
    echo "  ${C_DIM}No agents installed.${C_RESET}"
  fi
  echo ""
}

# ---------------------------------------------------------------------------
# Post-install verification: checks each tool's install directory for
# valid agent files (non-empty .md with YAML frontmatter).
# ---------------------------------------------------------------------------
verify_install() {
  header "Post-install verification"
  local ok_count=0 fail_count=0

  for t in "${SELECTED_TOOLS[@]}"; do
    local dest label
    case "$t" in
      claude-code) dest="${HOME}/.claude/agents"; label="Claude Code" ;;
      copilot)     dest="${HOME}/.github/agents"; label="Copilot" ;;
      antigravity) dest="${HOME}/.gemini/antigravity/skills"; label="Antigravity" ;;
      gemini-cli)  dest="${HOME}/.gemini/extensions/agency-agents/skills"; label="Gemini CLI" ;;
      opencode)    dest="${HOME}/.config/opencode/agents"; label="OpenCode" ;;
      openclaw)    dest="${HOME}/.openclaw/agency-agents"; label="OpenClaw" ;;
      cursor)      dest="${HOME}/.cursor/rules"; label="Cursor" ;;
      aider)       dest="${REPO_ROOT}"; label="Aider" ;;
      windsurf)    dest="${REPO_ROOT}"; label="Windsurf" ;;
      qwen)        dest="${HOME}/.qwen/agents"; label="Qwen Code" ;;
      kimi)        dest="${HOME}/.config/kimi/agents"; label="Kimi Code" ;;
      codex)       dest="${HOME}/.codex/agents"; label="Codex" ;;
      osaurus)     dest="${HOME}/.osaurus/skills"; label="Osaurus" ;;
      hermes)      dest="$(hermes_home_dir)/plugins"; label="Hermes" ;;
      *)           warn "Unknown tool: $t -- skipping verify"; continue ;;
    esac

    local count=0 bad=0
    if [[ -d "$dest" ]]; then
      while IFS= read -r -d '' f; do
        [[ -s "$f" ]] || { (( bad++ )) || true; continue; }
        local first; IFS= read -r first < "$f" 2>/dev/null || first=""
        [[ "$first" == "---" ]] || { (( bad++ )) || true; continue; }
        (( count++ )) || true
      done < <(find "$dest" -name "*.md" -type f -print0 2>/dev/null || true)
    fi

    if [[ "$count" -gt 0 ]]; then
      local warn_str=""
      [[ "$bad" -gt 0 ]] && warn_str=" (${bad} invalid)"
      ok "${label}: ${count} valid agents${warn_str}"
      (( ok_count++ )) || true
    else
      warn "${label}: no valid agents found (${bad} invalid files)"
      (( fail_count++ )) || true
    fi
  done

  printf "\n"
  ok "Verification complete: ${ok_count} passed, ${fail_count} failed"
  return $fail_count
}

# ---------------------------------------------------------------------------
# Dependency awareness -- reads depends_on.json (generated by convert.sh) and
# warns about installed agents whose declared dependencies are missing.
# ---------------------------------------------------------------------------
warn_missing_deps() {
  local manifest="$INTEGRATIONS/depends_on.json"
  [[ -f "$manifest" ]] || return 0

  # Parse depends_on.json with python3 (the file is JSON)
  local missing
  missing=$(python3 -c "
import json, sys, os
manifest = json.load(open('$manifest', encoding='utf-8'))
# Collect all installed agent IDs (from ~/.claude/agents/ or ~/.github/agents/)
installed = set()
dest_dirs = []
for d in [os.path.expanduser('~/.claude/agents'), os.path.expanduser('~/.github/agents'), os.path.expanduser('~/.copilot/agents')]:
    if os.path.isdir(d):
        for f in os.listdir(d):
            if f.endswith('.md'):
                installed.add(f.replace('.md', ''))
# Check each agent's deps
found = False
for agent_id, deps in sorted(manifest.items()):
    if agent_id in installed:
        missing_deps = [d for d in deps if d not in installed]
        if missing_deps:
            if not found:
                print('MISSING DEPENDENCIES:')
                found = True
            print(f'  {agent_id} depends on: {\", \".join(missing_deps)} — not installed')
" 2>/dev/null || true)

  if [[ -n "$missing" ]]; then
    echo ""
    warn "$missing"
  fi
}

# ---------------------------------------------------------------------------
# Parallel helpers
# ---------------------------------------------------------------------------

# Default parallel job count (nproc on Linux; sysctl on macOS when nproc missing)
parallel_jobs_default() {
  local n
  n=$(nproc 2>/dev/null) && [[ -n "$n" ]] && echo "$n" && return
  n=$(sysctl -n hw.ncpu 2>/dev/null) && [[ -n "$n" ]] && echo "$n" && return
  echo 4
}

# ---------------------------------------------------------------------------
# Per-tool install dispatch
# ---------------------------------------------------------------------------
install_tool() {
  ensure_converted "$1"
  case "$1" in
    claude-code) install_claude_code ;;
    copilot)     install_copilot     ;;
    antigravity) install_antigravity ;;
    gemini-cli)  install_gemini_cli  ;;
    opencode)    install_opencode    ;;
    openclaw)    install_openclaw    ;;
    cursor)      install_cursor      ;;
    aider)       install_aider       ;;
    windsurf)    install_windsurf    ;;
    qwen)        install_qwen        ;;
    kimi)        install_kimi        ;;
    codex)       install_codex       ;;
    osaurus)     install_osaurus     ;;
    hermes)      install_hermes      ;;
  esac
}
