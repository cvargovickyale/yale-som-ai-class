#!/usr/bin/env bash
# Publish hw5/ to the PUBLIC repo cvargovickyale/campus-customs-hw5.
# Exports only files git tracks in hw/hw_05/hw5 at HEAD (so .env, .venv,
# node_modules can never be included), mirrors them into a separate local
# clone, then commits and pushes. Safe to rerun after any fix.
# Unlike HW4, HW5 REQUIRES both databases under data/ (assignment rule).
set -euo pipefail
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
PUBLISH_DIR="$(dirname "$WORKSPACE")/campus-customs-hw5"
REMOTE="https://github.com/cvargovickyale/campus-customs-hw5.git"
MSG="${1:-Update hw5}"

cd "$WORKSPACE"
if [ -n "$(git status --porcelain hw/hw_05/hw5)" ]; then
  echo "Commit hw/hw_05/hw5 in the workspace repo first (uncommitted changes)." >&2; exit 1
fi
mkdir -p "$PUBLISH_DIR"
STAGE="$(mktemp -d)"
git archive HEAD hw/hw_05/hw5 | tar -x -C "$STAGE"
rsync -a --delete --exclude '.git' "$STAGE/hw/hw_05/hw5/" "$PUBLISH_DIR/hw5/"
rm -rf "$STAGE"

# Last line of defense: refuse secrets and dependencies...
if find "$PUBLISH_DIR/hw5" \( -name '.env' -o -name node_modules -o -name .venv -o -name '*.db-wal' -o -name '*.db-shm' -o -name '*.db-journal' \) | grep -q .; then
  echo "Refusing to publish: found .env, node_modules, .venv, or SQLite temp files" >&2; exit 1
fi
if grep -rqs "PORTKEY_API_KEY=[A-Za-z0-9_-]\{20,\}" "$PUBLISH_DIR/hw5"; then
  echo "Refusing to publish: something looks like a real Portkey key" >&2; exit 1
fi
# ...and require what the assignment says graders need.
for f in data/campus_customs.db data/campus_customs_new.db output/github_url.txt .env.example .mcp.json README.md; do
  [ -f "$PUBLISH_DIR/hw5/$f" ] || { echo "Refusing to publish: missing hw5/$f" >&2; exit 1; }
done

cd "$PUBLISH_DIR"
[ -d .git ] || { git init -q -b main; git remote add origin "$REMOTE"; }
git add -A
git diff --cached --quiet && { echo "Nothing to publish."; exit 0; }
git commit -q -m "$MSG"
git push -q -u origin main
git log --oneline -1
