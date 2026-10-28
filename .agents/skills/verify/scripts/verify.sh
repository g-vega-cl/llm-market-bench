#!/usr/bin/env bash
# Strict verification script for LLM Market Bench
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
cd "$REPO_ROOT"

RUN_ALL=true
FAST=false
ENGINE=false
WEB=false
HOTSPOTS_ONLY=false
SEQUENTIAL=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fast)
      FAST=true
      RUN_ALL=false
      shift
      ;;
    --engine)
      ENGINE=true
      RUN_ALL=false
      shift
      ;;
    --web)
      WEB=true
      RUN_ALL=false
      shift
      ;;
    --hotspots)
      HOTSPOTS_ONLY=true
      RUN_ALL=false
      shift
      ;;
    --sequential)
      SEQUENTIAL=true
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--fast] [--engine] [--web] [--hotspots] [--sequential]"
      exit 1
      ;;
  esac
done

if [ "$HOTSPOTS_ONLY" = true ]; then
  echo "--> Running Hotspot and Churn Forensics & refreshing wiki..."
  ./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 15 --write-wiki
  exit 0
fi

if [ "$RUN_ALL" = true ]; then
  ENGINE=true
  WEB=true
fi

echo "=================================================="
echo "  Code Verification Suite"
echo "=================================================="

# Synchronize Wiki: refresh hotspots, auto-index, and validate integrity
echo "--> Synchronizing Wiki (hotspots, indexes, and integrity)..."
./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 15 --write-wiki
./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py --fix

# Strict Wiki & Config Parity Linting (MANDATORY)
echo "--> Verifying strict Wiki integrity and config parity..."
./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py

# Auto-Wiki Pre-Commit Simulation (if non-doc code changes are staged)
STAGED_NON_DOC=$(git diff --cached --name-only 2>/dev/null | grep -vE '^(wiki/|raw/|docs/|scripts/auto-wiki|\.husky/)' || true)
if [ -n "$STAGED_NON_DOC" ]; then
  echo "--> Staged code changes detected; emulating auto-wiki pre-commit..."
  DIFF_FILE="$(mktemp /tmp/verify-auto-wiki-diff.XXXXXX)"
  git diff --cached > "$DIFF_FILE"
  if [ -s "$DIFF_FILE" ]; then
    ./apps/engine/.venv/bin/python3 apps/engine/auto_wiki.py --diff-file "$DIFF_FILE" --dry-run || {
      echo "ERROR: auto_wiki dry-run simulation failed on staged code changes!" >&2
      rm -f "$DIFF_FILE"
      exit 1
    }
  fi
  rm -f "$DIFF_FILE"
fi

# Re-index and embed QMD vector search if available
if command -v qmd >/dev/null 2>&1; then
  echo "--> Updating QMD vector index and embeddings..."
  qmd update
  qmd embed
fi

# Database & Migration Integrity
if [ -d "supabase/migrations" ]; then
  echo "--> Verifying database migration grants and RLS integrity..."
  ./apps/engine/.venv/bin/python3 -m pytest apps/engine/tests/test_migration_grants.py -q
fi


# Static checks & Hotspots
if [ "$ENGINE" = true ] || [ "$FAST" = true ]; then
  echo "--> Running Ruff lint check..."
  ./apps/engine/.venv/bin/ruff check apps/engine/

  echo "--> Running Ruff format check..."
  ./apps/engine/.venv/bin/ruff format --check apps/engine/

  echo "--> Checking Engine import root hygiene (zero forbidden 'apps.engine' in production code)..."
  if git grep -nE "(from|import) apps\.engine\." apps/engine/core/ apps/engine/tasks/ apps/engine/execution/ apps/engine/analytics/ apps/engine/tools/ apps/engine/local_autoresearch/ 2>/dev/null; then
    echo "ERROR: Engine production code must use module imports relative to apps/engine (e.g. 'from core.' or 'from local_autoresearch.', NOT 'from apps.engine.') to guarantee CI/CD parity!" >&2
    exit 1
  fi

  echo "--> Checking Bug Hotspots and Churn Forensics..."
  ./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 10
fi

if [ "$WEB" = true ] || [ "$FAST" = true ]; then
  echo "--> Running Biome check..."
  pnpm biome check
fi

# Typechecks & Builds
if [ "$WEB" = true ] || [ "$FAST" = true ]; then
  echo "--> Running TypeScript typecheck..."
  (cd apps/web && pnpm run typecheck)

  if [ "$FAST" = false ]; then
    echo "--> Running Web build..."
    (cd apps/web && pnpm run build)
  fi
fi

# Tests & Coverage
if [ "$FAST" = false ]; then
  if [ "$ENGINE" = true ]; then
    if [ "$SEQUENTIAL" = true ]; then
      echo "--> Running Hermetic Engine tests sequentially (1 worker, minimal CPU/RAM)..."
      (cd apps/engine && "$REPO_ROOT/apps/engine/.venv/bin/python3" -m pytest --cov=. --cov-config=.coveragerc)
    else
      echo "--> Running Hermetic Engine tests with coverage (matching CI working-directory: apps/engine)..."
      (cd apps/engine && "$REPO_ROOT/apps/engine/.venv/bin/python3" -m pytest -n auto --cov=. --cov-config=.coveragerc)
    fi
  fi

  if [ "$WEB" = true ]; then
    if [ "$SEQUENTIAL" = true ]; then
      echo "--> Running Web tests sequentially (1 worker, minimal CPU/RAM)..."
      (cd apps/web && pnpm test -- --maxWorkers=1 --coverage)
    else
      echo "--> Running Web tests with coverage..."
      (cd apps/web && pnpm test -- --coverage)
    fi
  fi
fi

echo "=================================================="
echo "✓ All verification checks passed cleanly."
echo "=================================================="
