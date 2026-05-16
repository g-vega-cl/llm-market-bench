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
import re
import sys
from pathlib import Path

import requests

# Configure logging using the centralized engine logger
from apps.engine.core.config import logger

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are performing a quality audit of a project wiki. The wiki is
a structured, interlinked knowledge base for the "LLM Market Bench" project.

Your task: read the wiki pages provided, then identify issues.

Look for:
1. **Contradictions**: Conflicting information between pages.
2. **Stale claims**: Outdated or superseded content.
3. **Missing pages**: Referenced concepts/entities that lack a page.
4. **Data gaps**: Crucial information missing from the project docs.
5. **Weak cross-references**: Related pages that should link but don't.
6. **Low-quality pages**: Thin or vague content.

GUIDELINES:
- Be concise. Focus on the most critical issues.
- Limit yourself to a maximum of 10 findings.
- Output ONLY valid JSON. No conversational text.
- Do NOT repeat yourself.

Output format:
{
  "findings": [
    {
      "severity": "high|medium|low",
      "type": "contradiction|stale|missing-page|data-gap|weak-link|thin",
      "pages": ["path/to/page.md"],
      "description": "Short, punchy description",
      "suggestion": "Actionable fix"
    }
  ],
  "summary": "One-sentence overview."
}
"""


def collect_wiki_content() -> str:
    """Read wiki pages. Truncates to stay within reasonable context limits."""
    parts = []
    # Only read the first 80k chars to ensure we don't blow the context window
    # and leave room for the model to think and respond.
    current_size = 0
    max_input_size = 80000

    for f in sorted(WIKI_DIR.rglob("*.md")):
        rel = str(f.relative_to(WIKI_DIR))
        if rel == "log.md":
            continue
        content = f.read_text()
        part = f"=== {rel} ===\n\n{content}\n"
        if current_size + len(part) > max_input_size:
            break
        parts.append(part)
        current_size += len(part)

    return "\n".join(parts)


def call_openrouter(content: str, model: str, api_key: str) -> dict:
    """Send wiki content to the LLM and return parsed findings."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Lint these wiki pages:\n\n{content}"},
        ],
        "temperature": 0.1,  # Lower temperature for more stable JSON
        "max_tokens": 4096,  # 4k is usually plenty for 10 findings and more stable than 8k on many providers
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anomalyco/llm-market-bench",
        "X-Title": "llm-market-bench wiki lint",
    }

    logger.info(f"Calling OpenRouter model: {model}")
    resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        logger.error(f"OpenRouter error response: {json.dumps(data, indent=2)}")
        error_msg = data["error"].get("message", "Unknown OpenRouter error")
        raise requests.RequestException(f"OpenRouter API error: {error_msg}")

    if not data.get("choices"):
        logger.error(f"OpenRouter unexpected response structure: {json.dumps(data, indent=2)}")
        raise requests.RequestException("OpenRouter returned no choices")

    choice = data["choices"][0]
    raw = choice.get("message", {}).get("content")
    finish_reason = choice.get("finish_reason")

    if raw is None:
        logger.error(f"OpenRouter returned empty content. Finish reason: {finish_reason}")
        raise requests.RequestException(f"OpenRouter returned empty content. Finish reason: {finish_reason}")

    if finish_reason == "length":
        logger.warning("LLM response was truncated due to max_tokens limit.")

    # Try to extract JSON from the response
    raw = raw.strip()

    # Strategy 1: Look for ```json ... ``` blocks
    json_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    for block in json_blocks:
        try:
            return json.loads(block)
        except json.JSONDecodeError:
            continue

    # Strategy 2: Look for anything starting with {
    for match in re.finditer(r"\{", raw):
        start_index = match.start()
        try:
            decoder = json.JSONDecoder()
            obj, end_index = decoder.raw_decode(raw[start_index:])
            # Basic validation that it's our expected schema
            if isinstance(obj, dict) and ("findings" in obj or "summary" in obj):
                return obj
        except json.JSONDecodeError:
            continue

    # Strategy 3: Try to parse the whole string
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        # Log more of the raw content to debug truncation
        logger.error(f"Raw content (len {len(raw)}):\n{raw}")
        raise


def main():
    parser = argparse.ArgumentParser(description="LLM wiki lint via OpenRouter")
    parser.add_argument("--model", help="OpenRouter model name (e.g., anthropic/claude-haiku-4-5)")
    args = parser.parse_args()

    model = args.model or os.getenv("WIKI_LINT_MODEL") or "deepseek/deepseek-v4-flash"
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)

    logger.info(f"Collecting wiki pages from: {WIKI_DIR}")
    content = collect_wiki_content()
    total_chars = len(content)
    total_files = len(list(WIKI_DIR.rglob("*.md")))
    logger.info(f"  {total_files} files, {total_chars} chars")

    try:
        result = call_openrouter(content, model, api_key)
    except requests.RequestException as e:
        logger.error(f"OpenRouter API error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        # Already logged the details in call_openrouter
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error during wiki lint: {e}")
        sys.exit(1)

    findings = result.get("findings", [])
    summary = result.get("summary", "No summary provided.")

    print(json.dumps({"findings": findings, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
