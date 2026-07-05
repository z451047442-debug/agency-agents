#!/usr/bin/env bash
#
# install-opencode.sh -- Install agents for OpenCode.

[[ -n "${_AGENCY_INSTALL_OPENCODE_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_OPENCODE_GUARD=1

install_opencode() {
  local src="$INTEGRATIONS/opencode"
  local dest; dest="$(resolve_dest opencode "${PWD}/.opencode/agents")"
  local count=0
  [[ -d "$src" ]] || { err "integrations/opencode missing. Run convert.sh first."; return 1; }
  # Support both flat layout (integrations/opencode/*.md) and nested (integrations/opencode/agents/*.md)
  local search_dir="$src"
  [[ -d "$src/agents" ]] && search_dir="$src/agents"
  mkdir -p "$dest"
  local f base
  while IFS= read -r -d '' f; do
    base="$(basename "$f")"
    [[ "$base" == "README.md" ]] && continue
    slug_allowed "${base%.md}" || continue
    install_file "$f" "$dest/"; incr count
  done < <(find "$search_dir" -maxdepth 1 -name "*.md" -print0)
  if (( count == 0 )); then
    warn "OpenCode: no agent files found in $search_dir. Run convert.sh --tool opencode first."
  else
    ok "OpenCode: $count agents -> $dest"
  fi
  capacity_warn opencode "$count"
  warn "OpenCode: project-scoped. Run from your project root to install there."
}
