---
tags: [auto-wiki, documentation, automation]
category: entity
---

# Auto-Wiki Documentation Generator

An automated system that reads staged git diffs and generates wiki documentation via LLM. It runs as part of the pre-commit hook, analyzing code changes and producing new entity pages, concept pages, log entries, and index updates without blocking the commit.

## Architecture

The auto-wiki system consists of two components:

- **`apps/engine/auto_wiki.py`** — Python script that collects the staged diff, sends it to an LLM (OpenRouter with ollama fallback), parses the JSON response, and writes wiki files
- **`scripts/auto-wiki.sh`** — Bash wrapper called from `.husky/pre-commit` that captures the diff, invokes the Python script, and re-stages any wiki changes

## LLM Integration

The script supports two LLM backends:

1. **OpenRouter** (primary) — uses `deepseek/deepseek-v4-pro` by default, configurable via `WIKI_DOC_MODEL` env var
2. **Ollama** (fallback) — uses `gemma4:31b` by default, configurable via `OLLAMA_MODEL` env var. It includes an **automatic dynamic fallback resolver**: if the requested model is not installed locally, it queries Ollama and falls back in order of preference (`gemma4:31b`, `qwen3.6:35b`, `llama3.1:8b`, etc.) or uses the first available local model instead of failing.

The OpenRouter API key is resolved from the `OPENROUTER_API_KEY` environment variable or the macOS keychain item `openrouter-api-key`.

## Safety & Design

- **Resource Preservation**: To save VRAM/RAM, Ollama models are queried with `"keep_alive": "10s"`, which keeps them warm for 10 seconds to speed up rapid consecutive queries while still ensuring they unload cleanly from system memory shortly afterwards. Furthermore, once the pre-commit lifecycle finishes (regardless of success or failure), the `auto-wiki.sh` script executes a cleanup trap that automatically terminates the local Ollama background server process (`pkill` routine) to conserve CPU/memory.
- **Non-blocking**: The pre-commit hook runs `auto-wiki.sh` with `|| true`, so wiki generation failures never block a commit
- **Path traversal protection**: The `write_new_page` function validates that the target path stays within the `wiki/` directory
- **Dry-run mode**: `--dry-run` prints the LLM response without writing files
- **Skip logic**: Only triggers when staged files include non-documentation changes (skips wiki/raw/docs-only commits)

## Related

- [[entities/engine]] — the Python engine that hosts the script
- [[concepts/rag-strategy]] — context injection patterns used in the system prompt
- [[concepts/tool-enforcement]] — similar pattern of LLM output validation
