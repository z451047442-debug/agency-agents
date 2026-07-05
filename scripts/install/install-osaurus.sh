#!/usr/bin/env bash
#
# install-osaurus.sh -- Install skills for Osaurus.

[[ -n "${_AGENCY_INSTALL_OSAURUS_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_OSAURUS_GUARD=1

install_osaurus() {
  local src="$INTEGRATIONS/osaurus"
  local dest; dest="$(resolve_dest osaurus "${HOME}/.osaurus/skills")"
  local count=0
  [[ -d "$src" ]] || { err "integrations/osaurus missing. Run convert.sh first."; return 1; }
  mkdir -p "$dest"
  local d
  while IFS= read -r -d '' d; do
    local name; name="$(basename "$d")"
    slug_allowed "$name" || continue
    mkdir -p "$dest/$name"
    install_file "$d/SKILL.md" "$dest/$name/SKILL.md"
    incr count
  done < <(find "$src" -mindepth 1 -maxdepth 1 -type d -print0)
  ok "Osaurus: $count skills -> $dest"
}
