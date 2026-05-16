#!/usr/bin/env python3
"""LLM-powered wiki lint via OpenRouter API.

Reads all wiki pages, sends them to an LLM for semantic analysis, outputs
structured findings as JSON for the GitHub Action to turn into an issue.

Usage:
    python apps/engine/wiki_lint_llm.py --model "anthropic/claude-haiku-4-5"

Env:
    OPENROUTER_API_KEY — required
    WIKI_LINT_MODEL     — fallback if --model not provided
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are performing a quality audit of a project wiki. The wiki is
a structured, interlinked knowledge base for the "LLM Market Bench" project — an
automated platform where multiple LLMs compete in a virtual stock market.

Your task: read all the wiki pages provided below, then identify issues.

Look for:
1. **Contradictions**: Page A says X, Page B says Y, and they conflict.
2. **Stale claims**: Information that appears outdated or superseded by newer content.
3. **Missing pages**: Concepts or entities mentioned in passing without their own page.
4. **Data gaps**: Questions the wiki should answer but doesn't. Information the project
   clearly needs documented but isn't.
5. **Weak cross-references**: Related pages that should link to each other but don't.
6. **Low-quality pages**: Pages that are too thin, vague, or need expansion.

Be specific. For each finding, include:
- The affected page(s) with file paths (e.g., entities/engine.md)
- A clear description of the issue
- A suggested fix

Output ONLY valid JSON in this exact format (no markdown, no explanation):
{
  "findings": [
    {
      "severity": "high|medium|low",
      "type": "contradiction|stale|missing-page|data-gap|weak-link|thin",
      "pages": ["path/to/page.md"],
      "description": "What's wrong",
      "suggestion": "How to fix it"
    }
  ],
  "summary": "One-sentence summary of overall wiki health"
}

If you find no issues, return {"findings": [], "summary": "Wiki looks clean."}
"""


def collect_wiki_content() -> str:
    """Read all wiki pages and return them as a single formatted string.
    Excludes log.md to save context for documentation content.
    """
    parts = []
    for f in sorted(WIKI_DIR.rglob("*.md")):
        rel = str(f.relative_to(WIKI_DIR))
        if rel == "log.md":
            continue
        content = f.read_text()
        parts.append(f"=== {rel} ===\n\n{content}\n")
    return "\n".join(parts)


def call_openrouter(content: str, model: str, api_key: str) -> dict:
    """Send wiki content to the LLM and return parsed findings."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Lint this wiki:\n\n{content[:100000]}"},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anomalyco/llm-market-bench",
        "X-Title": "llm-market-bench wiki lint",
    }

    resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        print(f"OpenRouter error response: {json.dumps(data, indent=2)}", file=sys.stderr)
        error_msg = data["error"].get("message", "Unknown OpenRouter error")
        raise requests.RequestException(f"OpenRouter API error: {error_msg}")

    if not data.get("choices"):
        print(f"OpenRouter unexpected response structure: {json.dumps(data, indent=2)}", file=sys.stderr)
        raise requests.RequestException("OpenRouter returned no choices")

    raw = data["choices"][0].get("message", {}).get("content")

    if raw is None:
        print(f"OpenRouter empty content response: {json.dumps(data, indent=2)}", file=sys.stderr)
        # Check for refusal or other reason
        finish_reason = data["choices"][0].get("finish_reason")
        raise requests.RequestException(f"OpenRouter returned empty content. Finish reason: {finish_reason}")

    # Try to extract JSON from the response (LLM may wrap in markdown)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(description="LLM wiki lint via OpenRouter")
    parser.add_argument("--model", help="OpenRouter model name (e.g., anthropic/claude-haiku-4-5)")
    args = parser.parse_args()

    model = args.model or os.getenv("WIKI_LINT_MODEL") or "deepseek/deepseek-v4-flash"
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        print("Error: OPENROUTER_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    print(f"Collecting wiki pages from: {WIKI_DIR}", file=sys.stderr)
    content = collect_wiki_content()
    total_chars = len(content)
    total_files = len(list(WIKI_DIR.rglob("*.md")))
    print(f"  {total_files} files, {total_chars} chars", file=sys.stderr)

    print(f"Calling OpenRouter model: {model}", file=sys.stderr)
    try:
        result = call_openrouter(content, model, api_key)
    except requests.RequestException as e:
        print(f"OpenRouter API error: {e}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM response: {e}", file=sys.stderr)
        sys.exit(1)

    findings = result.get("findings", [])
    summary = result.get("summary", "No summary provided.")

    print(json.dumps({"findings": findings, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
