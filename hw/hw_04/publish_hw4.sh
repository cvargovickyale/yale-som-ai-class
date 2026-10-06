#!/usr/bin/env bash
# Publish hw4/ to the PUBLIC repo cvargovickyale/campus-customs-hw4.
# Exports only files git tracks in hw/hw_04/hw4 at HEAD (so .env, data/,
# node_modules, .venv can never be included), mirrors them into a separate
# local clone, then commits and pushes. Safe to rerun after any fix.
set -euo pipefail
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLISH_DIR="$(dirname "$WORKSPACE")/campus-customs-hw4"
MSG="${1:-Update hw4}"

cd "$WORKSPACE"
if [ -n "$(git status --porcelain hw/hw_04/hw4)" ]; then
  echo "Commit hw/hw_04/hw4 in the workspace repo first (uncommitted changes)." >&2; exit 1
fi
mkdir -p "$PUBLISH_DIR"
STAGE="$(mktemp -d)"
git archive HEAD hw/hw_04/hw4 | tar -x -C "$STAGE"
rsync -a --delete --exclude '.git' "$STAGE/hw/hw_04/hw4/" "$PUBLISH_DIR/hw4/"
rm -rf "$STAGE"

# Last line of defense: refuse to publish secrets, data, or dependencies.
if find "$PUBLISH_DIR/hw4" \( -name '.env' -o -name '*.db' -o -path '*/data/*' -o -name node_modules -o -name .venv \) | grep -q .; then
  echo "Refusing to publish: found .env, a database, data/, node_modules, or .venv" >&2; exit 1
fi

cd "$PUBLISH_DIR"
[ -d .git ] || git init -q -b main
git add -A
git diff --cached --quiet && { echo "Nothing to publish."; exit 0; }
git commit -q -m "$MSG"
git push -q origin main 2>/dev/null || echo "(no remote yet)"
git log --oneline -1
