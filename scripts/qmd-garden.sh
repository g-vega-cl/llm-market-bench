#!/usr/bin/env bash
# Background QMD index/embedding refresh and read-only structural wiki audit.
# Runs via Fedora systemd --user timer outside git pre-commit and never mutates tracked files.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -s "$HOME/.nvm/nvm.sh" ]; then
  export NVM_DIR="$HOME/.nvm"
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh" >/dev/null 2>&1
  nvm use 24 >/dev/null 2>&1 || true
fi

if command -v qmd >/dev/null 2>&1; then
  echo "[qmd-garden] Running qmd update..."
  qmd update
  echo "[qmd-garden] Attempting background qmd embed..."
  qmd embed || echo "[qmd-garden] qmd embed skipped (GPU busy with Strata/Qwen); BM25 index is current."
fi

if [ -x "$REPO_ROOT/apps/engine/.venv/bin/python3" ]; then
  "$REPO_ROOT/apps/engine/.venv/bin/python3" "$REPO_ROOT/apps/engine/wiki_lint.py" --quiet || true
fi
