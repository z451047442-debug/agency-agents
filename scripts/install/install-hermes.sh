#!/usr/bin/env bash
#
# install-hermes.sh -- Install the lazy-router plugin for Hermes.

[[ -n "${_AGENCY_INSTALL_HERMES_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_HERMES_GUARD=1

install_hermes() {
  local src="$INTEGRATIONS/hermes/agency-agents-router"
  local hermes_home; hermes_home="$(hermes_home_dir)"
  local dest; dest="$(resolve_dest hermes "${hermes_home}/plugins/agency-agents-router")"
  [[ -f "$src/plugin.yaml" && -f "$src/__init__.py" && -f "$src/data/agents.json" ]] || {
    err "integrations/hermes/agency-agents-router missing. Run ./scripts/convert.sh --tool hermes first."
    return 1
  }
  mkdir -p "$dest"
  cp -r "$src"/. "$dest"/
  ok "Hermes: plugin installed -> $dest"
  if command -v hermes >/dev/null 2>&1; then
    warn "Hermes: restart the hermes service to activate the plugin"
  fi
}
