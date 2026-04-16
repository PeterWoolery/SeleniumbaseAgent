#!/usr/bin/env bash
# install.sh — curl-to-bash bootstrap. Clones the repo and runs setup.sh.
set -euo pipefail

REPO_URL="https://github.com/PeterWoolery/SeleniumbaseAgent.git"
TARGET_DIR="${SELENIUMBASE_DIR:-SeleniumbaseAgent}"

command -v git >/dev/null || { echo "git not found. Install git first." >&2; exit 1; }

if [ -d "$TARGET_DIR/.git" ]; then
  echo "==> $TARGET_DIR already exists; pulling latest"
  git -C "$TARGET_DIR" pull --ff-only
else
  echo "==> Cloning into $TARGET_DIR"
  git clone "$REPO_URL" "$TARGET_DIR"
fi

cd "$TARGET_DIR"
exec ./setup.sh
