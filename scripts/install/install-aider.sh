#!/usr/bin/env bash
#
# install-aider.sh -- Install CONVENTIONS.md for Aider.

[[ -n "${_AGENCY_INSTALL_AIDER_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_AIDER_GUARD=1

install_aider() {
  local src="$INTEGRATIONS/aider/CONVENTIONS.md"
  local dest="${PWD}/CONVENTIONS.md"
  [[ -f "$src" ]] || { err "integrations/aider/CONVENTIONS.md missing. Run convert.sh first."; return 1; }
  if [[ -f "$dest" ]]; then
    warn "Aider: CONVENTIONS.md already exists at $dest (remove to reinstall)."
    return 0
  fi
  install_file "$src" "$dest"
  ok "Aider: installed -> $dest"
  $SELECTION_ACTIVE && warn "Aider: single-file format -- team/agent filtering N/A (installs the full roster)."
  warn "Aider: project-scoped. Run from your project root to install there."
}
