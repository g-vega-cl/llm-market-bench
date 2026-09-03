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
import subprocess
import sys
from pathlib import Path

import requests

# Configure logging using the centralized engine logger
from core.config import logger

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
WIKI_DIR = REPO_ROOT / "wiki"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """You are performing a quality and code-drift audit of a project wiki. The wiki is
a structured, interlinked knowledge base for the "LLM Market Bench" project.

Your task: compare recent git commits against the provided wiki pages to identify documentation drift and inaccuracies.

Look for:
1. **Stale claims**: Wiki content describing an architecture, CLI command, default config, model name, or behavior that was changed or invalidated by the recent commits.
2. **Contradictions**: Discrepancies between the committed code and the documented behavior in these pages.
3. **Missing documentation**: Significant new capabilities, tools, or modules introduced in the commits that are omitted from the relevant wiki pages.
4. **Data gaps**: Crucial architectural details omitted from the project docs.

GUIDELINES:
- Base your findings strictly on discrepancies between the commits and the provided wiki pages.
- If the wiki pages accurately reflect the code or the commits do not invalidate them, return an empty findings list.
- Limit yourself to a maximum of 5 high-signal findings.
- Output ONLY valid JSON. No conversational text.
- Do NOT repeat yourself.

Output format:
{
  "findings": [
    {
      "severity": "high|medium|low",
      "type": "stale|contradiction|missing-doc|data-gap",
      "pages": ["path/to/page.md"],
      "description": "Short, punchy description of the drift",
      "suggestion": "Actionable fix or text update"
    }
  ],
  "summary": "One-sentence overview."
}
"""


def get_recent_commits(days: int = 7, repo_root: Path = REPO_ROOT) -> tuple[str, set[str]]:
    """Query git log for commits in the last N days, returning summary and changed code files."""
    try:
        raw_log = subprocess.check_output(
            [
                "git",
                "log",
                f"--since={days} days ago",
                "--pretty=format:COMMIT:%h %s",
                "--name-only",
            ],
            cwd=str(repo_root),
            text=True,
        )
    except Exception as e:
        logger.warning(f"Failed to query git log: {e}")
        return "", set()

    commit_lines = []
    changed_files = set()

    for line in raw_log.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("COMMIT:"):
            commit_lines.append(line)
        else:
            # Skip doc, asset, lockfile, and workflow paths
            if not line.startswith(("wiki/", "raw/", "docs/", ".husky/", ".github/")):
                changed_files.add(line)

    summary = "\n".join(commit_lines)
    return summary, changed_files


def find_matching_wiki_pages(
    changed_files: set[str],
    wiki_dir: Path = WIKI_DIR,
    max_pages: int = 8,
) -> list[str]:
    """Find wiki pages that document or reference the changed code files."""
    if not changed_files or not wiki_dir.is_dir():
        return []

    page_scores: dict[str, int] = {}
    wiki_files = [f for f in wiki_dir.rglob("*.md") if not str(f.relative_to(wiki_dir)).startswith("log")]

    for f in wiki_files:
        rel_wiki = str(f.relative_to(wiki_dir))
        content = f.read_text()
        score = 0

        for code_file in changed_files:
            file_path = Path(code_file)
            file_name = file_path.name
            stem = file_path.stem.replace("_", "-")

            if code_file in content:
                score += 3
            elif file_name in content or stem in rel_wiki:
                score += 2

        if score > 0:
            page_scores[rel_wiki] = score

    sorted_pages = sorted(page_scores.keys(), key=lambda p: page_scores[p], reverse=True)
    return sorted_pages[:max_pages]


def collect_wiki_content(
    matching_pages: list[str] | None = None,
    max_input_size: int = 120000,
    wiki_dir: Path = WIKI_DIR,
) -> str:
    """Read wiki pages. If matching_pages is given, read only those pages."""
    parts = []
    current_size = 0

    if matching_pages is not None:
        for rel in matching_pages:
            path = wiki_dir / rel
            if path.is_file():
                content = path.read_text()
                part = f"=== {rel} ===\n\n{content}\n"
                if current_size + len(part) > max_input_size:
                    break
                parts.append(part)
                current_size += len(part)
        return "\n".join(parts)

    for f in sorted(wiki_dir.rglob("*.md")):
        rel = str(f.relative_to(wiki_dir))
        if rel == "log.md" or rel.startswith("log/") or rel.startswith("log\\"):
            continue
        content = f.read_text()
        part = f"=== {rel} ===\n\n{content}\n"
        if current_size + len(part) > max_input_size:
            logger.warning(f"Truncating wiki content at {current_size} chars (max {max_input_size})")
            break
        parts.append(part)
        current_size += len(part)

    return "\n".join(parts)


def call_openrouter(
    content: str,
    model: str,
    api_key: str,
    all_files: list[str] | None = None,
    commits_summary: str = "",
) -> dict:
    """Send wiki content and recent commit summary to the LLM and return parsed findings."""
    if all_files is None:
        all_files = []

    user_parts = []
    if commits_summary:
        user_parts.append(f"Recent Git Commits:\n{commits_summary}\n")
    if all_files:
        user_parts.append(
            f"Here is a manifest of all files present in the wiki directory:\n"
            f"{json.dumps(all_files, indent=2)}\n\n"
            f"Use this manifest to verify if cross-referenced links/pages actually exist in the project "
            f"(even if their contents were truncated or not fully provided in the content below).\n"
        )
    user_parts.append(f"Lint these wiki pages:\n\n{content}")
    user_content = "\n".join(user_parts)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": user_content,
            },
        ],
        "temperature": 0.1,  # Lower temperature for more stable JSON
        "max_tokens": 16384,  # Provide sufficient headroom for reasoning + JSON output
        "reasoning": {
            "max_tokens": 4096,
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anomalyco/llm-market-bench",
        "X-Title": "llm-market-bench wiki lint",
    }

    logger.info(f"Calling OpenRouter model: {model}")
    resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=60)
    if not resp.ok:
        try:
            err_data = resp.json()
            error_msg = err_data.get("error", {}).get("message") or resp.text
        except Exception:
            error_msg = resp.text
        logger.error(f"OpenRouter API error response ({resp.status_code}): {error_msg}")
        raise requests.RequestException(f"OpenRouter API error ({resp.status_code}): {error_msg}")

    data = resp.json()

    if "error" in data:
        logger.error(f"OpenRouter error response: {json.dumps(data, indent=2)}")
        error_msg = data["error"].get("message", "Unknown OpenRouter error")
        raise requests.RequestException(f"OpenRouter API error: {error_msg}")

    if not data.get("choices"):
        logger.error(f"OpenRouter unexpected response structure: {json.dumps(data, indent=2)}")
        raise requests.RequestException("OpenRouter returned no choices")

    choice = data["choices"][0]
    msg = choice.get("message", {})
    raw = msg.get("content")
    reasoning = msg.get("reasoning") or msg.get("reasoning_content")
    finish_reason = choice.get("finish_reason")

    if raw is None or not raw.strip():
        if finish_reason == "length":
            error_detail = (
                "OpenRouter returned empty content because token limit was exhausted during reasoning "
                f"(finish_reason: length, reasoning_len: {len(reasoning) if reasoning else 0}). "
                "Consider increasing max_tokens or adjusting reasoning effort."
            )
            logger.error(error_detail)
            raise requests.RequestException(error_detail)
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
    parser.add_argument("--days", type=int, default=7, help="Number of days of git history to audit (default: 7)")
    args = parser.parse_args()

    model = args.model or os.getenv("WIKI_LINT_MODEL") or "deepseek/deepseek-v4-flash"
    api_key = os.getenv("OPENROUTER_API_KEY")

    if not api_key:
        logger.error("OPENROUTER_API_KEY not set")
        sys.exit(1)

    logger.info(f"Querying git history for past {args.days} days...")
    commits_summary, changed_files = get_recent_commits(days=args.days)

    if not changed_files:
        logger.info(f"No functional code changes detected in the past {args.days} days.")
        print(
            json.dumps(
                {
                    "findings": [],
                    "summary": f"No functional code changes detected in the past {args.days} days. Wiki is in sync with the codebase.",
                },
                indent=2,
            )
        )
        return

    logger.info(f"Found {len(changed_files)} changed code/config files across recent commits.")
    matching_pages = find_matching_wiki_pages(changed_files, wiki_dir=WIKI_DIR, max_pages=8)

    if not matching_pages:
        matching_pages = [
            p for p in ["overview.md", "entities/engine.md", "entities/pipeline.md"] if (WIKI_DIR / p).is_file()
        ]

    logger.info(f"Auditing {len(matching_pages)} relevant wiki pages: {matching_pages}")
    content = collect_wiki_content(matching_pages=matching_pages)
    total_chars = len(content)
    logger.info(f"Audit content size: {total_chars} chars")

    try:
        result = call_openrouter(content, model, api_key, commits_summary=commits_summary)
    except requests.RequestException as e:
        logger.error(f"OpenRouter API error: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response after multiple strategies")
        sys.exit(1)
    except Exception:
        logger.exception("Unexpected error during wiki lint")
        sys.exit(1)

    findings = result.get("findings", [])
    summary = result.get("summary", "No summary provided.")

    print(json.dumps({"findings": findings, "summary": summary}, indent=2))


if __name__ == "__main__":
    main()
