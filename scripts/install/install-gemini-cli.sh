#!/usr/bin/env bash
#
# install-gemini-cli.sh -- Install agents for Gemini CLI.

[[ -n "${_AGENCY_INSTALL_GEMINI_CLI_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_GEMINI_CLI_GUARD=1

install_gemini_cli() {
  local src="$INTEGRATIONS/gemini-cli/agents"
  local dest; dest="$(resolve_dest gemini-cli "${HOME}/.gemini/agents")"
  local count=0
  [[ -d "$src" ]] || { err "integrations/gemini-cli/agents missing. Run ./scripts/convert.sh --tool gemini-cli first."; return 1; }
  mkdir -p "$dest"
  local f
  while IFS= read -r -d '' f; do
    slug_allowed "$(basename "$f" .md)" || continue
    install_file "$f" "$dest/"
    incr count
  done < <(find "$src" -maxdepth 1 -name "*.md" -print0)
  ok "Gemini CLI: $count agents -> $dest"
}
