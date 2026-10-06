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
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--fast] [--engine] [--web] [--hotspots]"
      exit 1
      ;;
  esac
done

if [ "$HOTSPOTS_ONLY" = true ]; then
  echo "--> Running Hotspot and Churn Forensics..."
  ./apps/engine/.venv/bin/python3 apps/engine/hotspots.py --since "60 days ago" --top 15
  exit 0
fi

if [ "$RUN_ALL" = true ]; then
  ENGINE=true
  WEB=true
fi

echo "=================================================="
echo "  Code Verification Suite"
echo "=================================================="

# Always run Wiki integrity check (takes <0.1s, guards against broken code references)
echo "--> Running Wiki integrity check..."
./apps/engine/.venv/bin/python3 apps/engine/wiki_lint.py

# Static checks & Hotspots
if [ "$ENGINE" = true ] || [ "$FAST" = true ]; then
  echo "--> Running Ruff lint check..."
  ./apps/engine/.venv/bin/ruff check apps/engine/

  echo "--> Running Ruff format check..."
  ./apps/engine/.venv/bin/ruff format --check apps/engine/

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
    echo "--> Running Hermetic Engine tests with coverage..."
    ./apps/engine/.venv/bin/python3 -m pytest -n auto --cov=. --cov-config=.coveragerc
  fi

  if [ "$WEB" = true ]; then
    echo "--> Running Web tests with coverage..."
    (cd apps/web && pnpm test -- --coverage)
  fi
fi

echo "=================================================="
echo "✓ All verification checks passed cleanly."
echo "=================================================="
