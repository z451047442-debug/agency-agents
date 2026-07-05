#!/usr/bin/env bash
#
# install-codex.sh -- Install custom agent TOML files for Codex.

[[ -n "${_AGENCY_INSTALL_CODEX_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_CODEX_GUARD=1

install_codex() {
  local src="$INTEGRATIONS/codex/agents"
  local dest; dest="$(resolve_dest codex "${HOME}/.codex/agents")"
  local count=0

  [[ -d "$src" ]] || { err "integrations/codex/agents missing. Run convert.sh first."; return 1; }

  mkdir -p "$dest"

  local f
  while IFS= read -r -d '' f; do
    local base; base="$(basename "$f")"
    [[ "$base" == "README.md" ]] && continue
    slug_allowed "$(basename "$f" .toml)" || continue
    install_file "$f" "$dest/"
    incr count
  done < <(find "$src" -maxdepth 1 -type f -print0)

  ok "Codex: $count agents -> $dest"
}
