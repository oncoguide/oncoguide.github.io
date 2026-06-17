#!/usr/bin/env bash
# Encrypt /andreea/ personal health hub pages with staticrypt.
#
# Mirror of encrypt-dorin.sh for the /andreea/ private health node.
#
# Source HTML (unencrypted, contains PII) lives outside this repo at:
#   $ANDREEA_SOURCE (default: ~/Documents/personal-agent-dorin/.private/andreea/source)
#
# Encrypted output goes to:
#   $REPO/static/andreea/
#
# Password source (in order of precedence):
#   1. $ANDREEA_PASSWORD env var (used by CI)
#   2. ~/Documents/personal-agent-dorin/.private/clinical/password.txt
#      (intentional: same password as /clinical/ and /dorin/, single source of truth)
#   3. Interactive prompt (fallback)
#
# Usage:  bash scripts/encrypt-andreea.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${ANDREEA_SOURCE:-$HOME/Documents/personal-agent-dorin/.private/andreea/source}"
DEST_DIR="$REPO_ROOT/static/andreea"
PW_FILE="$HOME/Documents/personal-agent-dorin/.private/clinical/password.txt"
ITERATIONS=500000

if [[ ! -d "$SOURCE_DIR" ]]; then
  echo "ERROR: source dir not found: $SOURCE_DIR" >&2
  exit 1
fi

# Resolve password (same as /clinical/ + /dorin/ — shared password by design)
if [[ -n "${ANDREEA_PASSWORD:-}" ]]; then
  PW="$ANDREEA_PASSWORD"
  echo "[encrypt-andreea] using password from \$ANDREEA_PASSWORD env var"
elif [[ -r "$PW_FILE" ]]; then
  PW="$(tr -d '\n' < "$PW_FILE")"
  echo "[encrypt-andreea] using password from $PW_FILE (same as /clinical/ + /dorin/)"
else
  read -rsp "Enter staticrypt password (same as /clinical/): " PW
  echo
fi

if [[ -z "$PW" ]]; then
  echo "ERROR: password is empty" >&2
  exit 1
fi

# Clean dest
rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

# Copy sources to dest, then encrypt in place
cp "$SOURCE_DIR"/*.html "$DEST_DIR/"

# Encrypt each HTML file. --short: compact URL. --iterations: PBKDF2 hardening.
# -d: output dir = same dir (in-place). --remember 0: don't persist password in localStorage across sessions.
cd "$DEST_DIR"
for f in *.html; do
  echo "[encrypt-andreea] $f"
  npx --yes staticrypt "$f" \
    --password "$PW" \
    --short \
    --remember 0 \
    -d "$DEST_DIR" \
    -o "$f"
done

echo "[encrypt-andreea] done. Encrypted files in: $DEST_DIR"
ls -la "$DEST_DIR"
