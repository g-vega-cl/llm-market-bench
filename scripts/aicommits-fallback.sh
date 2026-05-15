#!/usr/bin/env bash

# Wrapper for aicommits that falls back to Ollama on failure
# Usage: ./scripts/aicommits-fallback.sh [aicommits args]

# 1. Try standard aicommits (OpenRouter)
if aicommits "$@"; then
    exit 0
fi

echo "  [aicommits] OpenRouter failed, falling back to Ollama (qwen3.5)..."

# 2. Temporarily reconfigure aicommits for Ollama
# We use 'aicommits config set' which modifies ~/.aicommits
# To avoid permanent changes, we'll restore the original config after.

CONFIG_FILE="$HOME/.aicommits"
TEMP_CONFIG_FILE="$(mktemp /tmp/aicommits-config.XXXXXX)"

# Backup current config
cp "$CONFIG_FILE" "$TEMP_CONFIG_FILE"

# Reconfigure for Ollama
aicommits config set OPENAI_BASE_URL=http://localhost:11434/v1 > /dev/null
aicommits config set OPENAI_MODEL=qwen3.5:latest > /dev/null
aicommits config set OPENAI_API_KEY=ollama > /dev/null

# Try again with Ollama
aicommits "$@"

# Restore original config
mv "$TEMP_CONFIG_FILE" "$CONFIG_FILE"
