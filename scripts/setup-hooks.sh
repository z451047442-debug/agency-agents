#!/usr/bin/env bash
#
# setup-hooks.sh — Install git hooks for The Agency.
#
# Usage:
#   ./scripts/setup-hooks.sh          # install all hooks
#   ./scripts/setup-hooks.sh --list   # list installed hooks
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_SRC="$SCRIPT_DIR/git-hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

list_hooks() {
  echo "Available hooks:"
  for hook in "$HOOKS_SRC"/*; do
    [[ "$(basename "$hook")" == "README.md" ]] && continue
    local installed=""
    [[ -f "$HOOKS_DST/$(basename "$hook")" ]] && installed=" (installed)"
    echo "  $(basename "$hook")$installed"
  done
}

case "${1:-}" in
  --list|-l)
    list_hooks
    exit 0
    ;;
  --help|-h)
    sed -n '3,6p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
esac

mkdir -p "$HOOKS_DST"

installed=0
for hook in "$HOOKS_SRC"/*; do
  name="$(basename "$hook")"
  [[ "$name" == "README.md" ]] && continue
  cp "$hook" "$HOOKS_DST/$name"
  chmod +x "$HOOKS_DST/$name"
  echo "  Installed: $name"
  installed=$((installed + 1))
done

echo ""
echo "Done — $installed hook(s) installed."
echo "Run 'scripts/setup-hooks.sh --list' to verify."
