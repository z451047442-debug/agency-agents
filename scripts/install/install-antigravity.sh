#!/usr/bin/env bash
#
# install-antigravity.sh -- Install skills for Antigravity.

[[ -n "${_AGENCY_INSTALL_ANTIGRAVITY_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_ANTIGRAVITY_GUARD=1

install_antigravity() {
  local src="$INTEGRATIONS/antigravity"
  local dest; dest="$(resolve_dest antigravity "${HOME}/.gemini/antigravity/skills")"
  local count=0
  [[ -d "$src" ]] || { err "integrations/antigravity missing. Run convert.sh first."; return 1; }
  mkdir -p "$dest"
  local d
  while IFS= read -r -d '' d; do
    local name; name="$(basename "$d")"
    slug_allowed "$name" || continue
    mkdir -p "$dest/$name"
    install_file "$d/SKILL.md" "$dest/$name/SKILL.md"
    incr count
  done < <(find "$src" -mindepth 1 -maxdepth 1 -type d -print0)
  ok "Antigravity: $count skills -> $dest"
}
