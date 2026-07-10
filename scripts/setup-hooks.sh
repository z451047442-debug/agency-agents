#!/usr/bin/env bash
# Install git hooks from scripts/git-hooks/ into .git/hooks/
set -e
HOOKS_DIR="$(cd "$(dirname "$0")" && pwd)/git-hooks"
GIT_HOOKS="$(cd "$(dirname "$0")/.." && pwd)/.git/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "No git-hooks directory found at $HOOKS_DIR"
    exit 0
fi

for hook in "$HOOKS_DIR"/*; do
    name=$(basename "$hook")
    # Skip non-executable and sample files
    if [ -x "$hook" ] && [ "${name%.sample}" = "$name" ]; then
        cp "$hook" "$GIT_HOOKS/$name"
        chmod +x "$GIT_HOOKS/$name"
        echo "  Installed: $name"
    fi
done
echo "Git hooks installed."
