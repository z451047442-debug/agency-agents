#!/usr/bin/env bash
#
# install-openclaw.sh -- Install workspaces for OpenClaw.

[[ -n "${_AGENCY_INSTALL_OPENCLAW_GUARD:-}" ]] && return 0
_AGENCY_INSTALL_OPENCLAW_GUARD=1

install_openclaw() {
  local src="$INTEGRATIONS/openclaw"
  local dest; dest="$(resolve_dest openclaw "${HOME}/.openclaw/agency-agents")"
  local count=0
  local existing_agents=""
  [[ -d "$src" ]] || { err "integrations/openclaw missing. Run convert.sh first."; return 1; }
  mkdir -p "$dest"
  if command -v openclaw >/dev/null 2>&1; then
    existing_agents=$'\n'"$(openclaw agents list --json 2>/dev/null | sed -n 's/^[[:space:]]*\"id\": \"\\([^\"]*\\)\".*/\\1/p')"$'\n'
  fi
  local d
  while IFS= read -r -d '' d; do
    local name; name="$(basename "$d")"
    slug_allowed "$name" || continue
    [[ -f "$d/SOUL.md" && -f "$d/AGENTS.md" && -f "$d/IDENTITY.md" ]] || continue
    mkdir -p "$dest/$name"
    install_file "$d/SOUL.md" "$dest/$name/SOUL.md"
    install_file "$d/AGENTS.md" "$dest/$name/AGENTS.md"
    install_file "$d/IDENTITY.md" "$dest/$name/IDENTITY.md"
    if command -v openclaw >/dev/null 2>&1; then
      if [[ "$existing_agents" != *$'\n'"$name"$'\n'* ]]; then
        openclaw agents add "$name" --workspace "$dest/$name" --non-interactive || true
      fi
    fi
    (( count++ )) || true
  done < <(find "$src" -mindepth 1 -maxdepth 1 -type d -print0)
  if (( count == 0 )); then
    err "integrations/openclaw contains no generated workspaces. Run ./scripts/convert.sh --tool openclaw first."
    return 1
  fi
  ok "OpenClaw: $count workspaces -> $dest"
  if command -v openclaw >/dev/null 2>&1; then
    warn "OpenClaw: run 'openclaw gateway restart' to activate new agents"
  fi
}
