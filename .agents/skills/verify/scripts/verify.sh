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
  EMBED_OUT="$(mktemp /tmp/verify-qmd-embed.XXXXXX)"
  if ! qmd embed > "$EMBED_OUT" 2>&1; then
    if grep -iqE "cuda error|out of memory" "$EMBED_OUT"; then
      echo "--> Warning: qmd embed skipped due to GPU VRAM constraint; BM25 search remains fully updated."
    else
      cat "$EMBED_OUT" >&2
      rm -f "$EMBED_OUT"
      echo "ERROR: qmd embed failed with non-CUDA error!" >&2
      exit 1
    fi
  fi
  rm -f "$EMBED_OUT"
fi

# Database & Migration Integrity
if [ -d "supabase/migrations" ]; then
  echo "--> Verifying database migration grants and RLS integrity..."
  ./apps/engine/.venv/bin/python3 -m pytest apps/engine/tests/test_migration_grants.py -q

  # Detect any modified or newly added migrations in working tree, staged, or recent commit
  MIGRATIONS_TOUCHED=$(git diff --name-only HEAD~1 HEAD -- supabase/migrations/ 2>/dev/null || true)
  MIGRATIONS_DIRTY=$(git status --porcelain -- supabase/migrations/ 2>/dev/null || true)
  if [ -n "$MIGRATIONS_TOUCHED" ] || [ -n "$MIGRATIONS_DIRTY" ]; then
    echo "--> [DATABASE / REPLICA MANDATE] Database migrations detected in recent changes:"
    echo "    NOTE: Physical PostgreSQL streaming replication to the secondary MiniPC edge"
    echo "    (cv-minipc@minipc) does NOT propagate NOTIFY events (NOTIFY pgrst, 'reload schema')."
    echo "    Standby PostgREST does NOT auto-reload its schema cache without container restart."
    echo "    MANDATORY ACTION: Deploy to secondary edge and reload schema cache:"
    echo "      ./docker/archive/deploy_secondary.sh cv-minipc@minipc"
    echo "    Verify live read probe against SUPABASE_PROJECT_URL (https://benchify-archive-db.clvg.uk) with zero PGRST205 errors."
  fi
fi


# Static checks & Hotspots
if [ "$ENGINE" = true ] || [ "$FAST" = true ]; then
  echo "--> Running Ruff lint check..."
  ./apps/engine/.venv/bin/ruff check apps/engine/

  echo "--> Running Ruff format check..."
  ./apps/engine/.venv/bin/ruff format --check apps/engine/

  # Check McCabe cyclomatic complexity on modified Python files (Diff-scoped check)
  MODIFIED_PY=$(git diff --name-only HEAD -- 'apps/engine/**/*.py' 'apps/engine/*.py' 2>/dev/null || true)
  if [ -n "$MODIFIED_PY" ]; then
    echo "--> Auditing McCabe Cyclomatic Complexity (C901 <= 15) on modified Python files..."
    ./apps/engine/.venv/bin/ruff check $MODIFIED_PY --select C901 --config "lint.mccabe.max-complexity = 15" || \
      echo "WARNING: High cyclomatic complexity (>15) detected in modified files. Review in Tier 7 (extract pure helpers or guard clauses)."

    echo "--> Checking for silent exception swallowing (suppress(Exception) or unlogged pass)..."
    PROD_PY=$(echo "$MODIFIED_PY" | grep -vE 'test_|_test\.py|/tests/' || true)
    if [ -n "$PROD_PY" ]; then
      if grep -nE "contextlib\.suppress\(Exception\)|suppress\(Exception\)" $PROD_PY 2>/dev/null; then
        echo "ERROR: contextlib.suppress(Exception) is forbidden in production engine code! Catch specific exceptions or log with logger.exception." >&2
        exit 1
      fi
    fi
  fi

  echo "--> Checking for shotgun surgery (production files blast radius)..."
  TOUCHED_PROD=$(git diff --name-only HEAD -- 'apps/' 'packages/' 2>/dev/null | grep -vE 'test|/tests/|__tests__|\.test\.|\.spec\.' || true)
  TOUCHED_COUNT=$(echo "$TOUCHED_PROD" | grep -c . || true)
  if [ "$TOUCHED_COUNT" -gt 10 ]; then
    echo "WARNING [SHOTGUN SURGERY]: Diff modifies $TOUCHED_COUNT production files (>10). Tier 7 review MUST audit for leaky abstractions or coupling debt."
  fi

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
