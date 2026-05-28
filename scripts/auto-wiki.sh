#!/usr/bin/env bash
# Auto-document staged code changes in the wiki.
#
# Called from .husky/pre-commit — runs after the existing lint checks.
# Only triggers when there are code changes (not just wiki/raw/doc changes).
#
# Exit code 0 always — wiki doc failures should never block a commit.

set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
DIFF_FILE="$(mktemp /tmp/auto-wiki-diff.XXXXXX)"
PYTHON="${REPO_ROOT}/apps/engine/.venv/bin/python3"
SCRIPT="${REPO_ROOT}/apps/engine/auto_wiki.py"

cleanup() {
    rm -f "$DIFF_FILE"
    # Stop local Ollama server process after run is complete
    echo "[auto-wiki] stopping local Ollama service..."
    pkill -f "ollama serve" || pkill ollama || true
}
trap cleanup EXIT

# Only run if there are code changes (skip wiki-only, raw-only, docs-only commits)
STAGED_FILES="$(git diff --cached --name-only)"
if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Check if ALL staged files are in wiki/, raw/, docs/, or scripts/auto-wiki
NON_DOC_FILES=$(echo "$STAGED_FILES" | grep -vE '^(wiki/|raw/|docs/|scripts/auto-wiki|\.husky/)' || true)
if [ -z "$NON_DOC_FILES" ]; then
    echo "[auto-wiki] skipping — only doc/wiki/config files changed"
    exit 0
fi

# Capture the staged diff
git diff --cached > "$DIFF_FILE"

if [ ! -s "$DIFF_FILE" ]; then
    echo "[auto-wiki] skipping — empty diff"
    exit 0
fi

if [ ! -x "$PYTHON" ]; then
    echo "[auto-wiki] skipping — python not found at $PYTHON"
    exit 0
fi

echo "[auto-wiki] analyzing staged changes..."

# Run the auto-wiki script — BLOCKING
"$PYTHON" "$SCRIPT" --diff-file "$DIFF_FILE" || {
    echo "[auto-wiki] documentation generation failed (commit BLOCKED)"
    exit 1
}

# Run the pipeline compiler to keep the web app's How It Works in sync
COMPILE_SCRIPT="${REPO_ROOT}/apps/engine/scripts/compile_how_it_works.py"
if [ -f "$COMPILE_SCRIPT" ]; then
    echo "[auto-wiki] compiling How It Works page..."
    "$PYTHON" "$COMPILE_SCRIPT" || echo "[auto-wiki] WARNING: How It Works compilation failed"
fi

# Re-stage wiki and compiled changes so they're included in the commit
if git diff --name-only -- wiki/ apps/web/src/config/how-it-works.json | grep -q .; then
    echo "[auto-wiki] staging updated files..."
    git add wiki/ apps/web/src/config/how-it-works.json
fi
