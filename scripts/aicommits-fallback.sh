#!/usr/bin/env bash

# Wrapper for aicommits that falls back to Ollama on failure
# Usage: ./scripts/aicommits-fallback.sh [aicommits args]

# 1. Try standard aicommits (OpenRouter)
if AICOMMITS_CONFIG_PATH="$HOME/.aicommits" aicommits "$@"; then
    exit 0
fi

echo "  [aicommits] OpenRouter failed, falling back to Ollama (qwen3.5)..."

# 2. Use Ollama config file (no need to modify ~/.aicommits)
if AICOMMITS_CONFIG_PATH="$HOME/.aicommits-ollama" aicommits "$@"; then
    exit 0
fi

# If both fail, exit with error
echo "  [aicommits] Both OpenRouter and Ollama failed"
exit 1
