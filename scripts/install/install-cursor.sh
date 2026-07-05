#!/usr/bin/env bash
#
# install-cursor.sh -- Install rules for Cursor.

[[ -n "${_AGENCY_INSTALL_CURSOR_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_CURSOR_GUARD=1

install_cursor() {
  local src="$INTEGRATIONS/cursor/rules"
  local dest; dest="$(resolve_dest cursor "${PWD}/.cursor/rules")"
  local count=0
  [[ -d "$src" ]] || { err "integrations/cursor missing. Run convert.sh first."; return 1; }
  mkdir -p "$dest"
  local f
  while IFS= read -r -d '' f; do
    slug_allowed "$(basename "$f" .mdc)" || continue
    install_file "$f" "$dest/"; incr count
  done < <(find "$src" -maxdepth 1 -name "*.mdc" -print0)
  ok "Cursor: $count rules -> $dest"
  warn "Cursor: project-scoped. Run from your project root to install there."
}
