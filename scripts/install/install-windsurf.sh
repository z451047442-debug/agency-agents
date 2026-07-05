#!/usr/bin/env bash
#
# install-windsurf.sh -- Install .windsurfrules for Windsurf.

[[ -n "${_AGENCY_INSTALL_WINDSURF_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_WINDSURF_GUARD=1

install_windsurf() {
  local src="$INTEGRATIONS/windsurf/.windsurfrules"
  local dest="${PWD}/.windsurfrules"
  [[ -f "$src" ]] || { err "integrations/windsurf/.windsurfrules missing. Run convert.sh first."; return 1; }
  if [[ -f "$dest" ]]; then
    warn "Windsurf: .windsurfrules already exists at $dest (remove to reinstall)."
    return 0
  fi
  install_file "$src" "$dest"
  ok "Windsurf: installed -> $dest"
  $SELECTION_ACTIVE && warn "Windsurf: single-file format -- team/agent filtering N/A (installs the full roster)."
  warn "Windsurf: project-scoped. Run from your project root to install there."
}
