#!/usr/bin/env bash
#
# install-oh-my-claudecode.sh -- Install the OMC (oh-my-claudecode) smart plugin.

[[ -n "${_AGENCY_INSTALL_OMC_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_OMC_GUARD=1

install_oh_my_claudecode() {
  local src="$INTEGRATIONS/oh-my-claudecode"
  local claude_home; claude_home="${HOME}/.claude"
  [[ -d "$src/skills" || -f "$src/model-routing.json" ]] || {
    err "integrations/oh-my-claudecode missing. Run ./scripts/convert.sh --tool oh-my-claudecode first."
    return 1
  }
  mkdir -p "$claude_home"
  if [[ -d "$src/skills" ]]; then
    mkdir -p "$claude_home/skills"
    cp -r "$src/skills/." "$claude_home/skills/"
  fi
  local f
  for f in model-routing.json hooks.json team-config.json; do
    [[ -f "$src/$f" ]] && cp "$src/$f" "$claude_home/$f"
  done
  ok "oh-my-claudecode: OMC plugin installed -> $claude_home"
}
