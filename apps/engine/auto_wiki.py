#!/usr/bin/env python3
"""Auto-document staged code changes into the wiki.

Reads git diff --cached, sends it to an LLM (OpenRouter → ollama fallback),
and writes new wiki pages, log entries, and index updates.

Usage:
    python apps/engine/auto_wiki.py --diff-file /tmp/diff.txt

Env / keychain:
    OPENROUTER_API_KEY        — preferred
    macOS keychain item
      "openrouter-api-key"    — fallback (security find-generic-password)
    WIKI_DOC_MODEL            — override default model
    OLLAMA_MODEL              — fallback model (default: qwen3)

Exit code 0 = no changes needed or success. Non-zero = error (printed to stderr).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)
WIKI_DIR = REPO_ROOT / "wiki"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_URL = "http://localhost:11434/api/chat"

DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"


def get_api_key() -> str | None:
    """Resolve OpenRouter API key: env var first, then macOS keychain."""
    key = os.getenv("OPENROUTER_API_KEY")
    if key:
        return key
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "openrouter-api-key", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def collect_wiki_context() -> str:
    """Read scaffold wiki files for LLM context (not the full wiki)."""
    parts = []
    for fname in ("SCHEMA.md", "overview.md", "index.md"):
        path = WIKI_DIR / fname
        if path.is_file():
            parts.append(f"=== wiki/{fname} ===\n\n{path.read_text()}\n")
    # List existing pages
    pages = []
    for f in sorted(WIKI_DIR.rglob("*.md")):
        rel = str(f.relative_to(WIKI_DIR))
        pages.append(f"  wiki/{rel}")
    parts.append("=== Existing wiki pages ===\n\n" + "\n".join(pages) + "\n")
    # Read staged raw/ documents so the LLM sees human-written design intent
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "--", "raw/"],
            capture_output=True, text=True, timeout=5, cwd=REPO_ROOT,
        )
        if result.returncode == 0 and result.stdout.strip():
            raw_files = result.stdout.strip().split("\n")
            raw_context = []
            for rel_path in raw_files:
                full_path = REPO_ROOT / rel_path
                if full_path.is_file():
                    raw_context.append(f"=== staged: {rel_path} ===\n\n{full_path.read_text()}\n")
            if raw_context:
                parts.append("=== Staged raw/ documents (human-written design context) ===\n\n" + "\n".join(raw_context))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return "\n".join(parts)


SYSTEM_PROMPT = """You are a wiki documentation agent for the "LLM Market Bench" project —
an automated platform where multiple LLMs compete in a virtual stock market.

You receive a git diff of staged code changes. Your job is to determine if wiki
documentation updates are needed and produce structured JSON.

## Wiki Conventions

The wiki lives at wiki/ with this structure:
  entities/   — one page per major component (engine, database, etc.)
  concepts/   — one page per key idea (consensus, tool-enforcement, etc.)
  interactions/ — promoted Q&A discussions
  sources/    — synthesized summaries of raw/docs/ files
  index.md    — content catalog with [[links]]
  log.md      — append-only chronological record
  overview.md — high-level project synthesis
  SCHEMA.md   — conventions documentation

Every page starts with YAML frontmatter:
  ---
  tags: [tag1, tag2]
  category: entity|concept|source|synthesis|interaction
  ---

Cross-references use [[entities/page-name]] style. Naming is kebab-case.

Log entries use format: ## [YYYY-MM-DD] type | Title

Never delete content — strike through or mark superseded instead.

## What to Document

- **New modules/packages/apps** → create entity page in entities/
- **New ideas/patterns/abstractions** → create concept page in concepts/
- **Any non-trivial code change** → append log entry
- **Significant refactors** → append log entry
- **Bug fixes with impact** → append log entry

## What to Skip

- Typo fixes, formatting, comment changes
- Trivial refactors with no behavioral impact
- Test-only changes that just add coverage
- Changes to wiki/ or raw/ or docs/ themselves

## Output Format

Output ONLY valid JSON (no markdown, no explanation, no code fences):

{
  "should_update": true,
  "log_entry": "## [YYYY-MM-DD] type | Title\\n\\nDescription...",
  "new_pages": [
    {
      "path": "entities/my-feature.md",
      "content": "---\\ntags: [...]\\ncategory: entity\\n---\\n\\n# My Feature\\n\\n..."
    }
  ],
  "index_additions": [
    {"section": "Entities", "entry": "- [[entities/my-feature]] — one-line description"}
  ]
}

If no documentation is needed, return:
{"should_update": false}

For the log_entry, use the actual current date.
"""


def call_openrouter(prompt: str, model: str, api_key: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
        "response_format": {"type": "json_object"},
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/anomalyco/llm-market-bench",
        "X-Title": "llm-market-bench auto wiki",
    }

    resp = requests.post(OPENROUTER_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    return _parse_llm_response(resp.json()["choices"][0]["message"]["content"])


def get_available_ollama_models() -> list[str]:
    """Fetch list of models available in local Ollama instance."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        if resp.status_code == 200:
            return [m["name"] for m in resp.json().get("models", [])]
    except requests.RequestException:
        pass
    return []


def call_ollama(prompt: str, model: str) -> dict:
    system_prompt = SYSTEM_PROMPT + "\n\nIMPORTANT: Output ONLY the JSON. No markdown, no explanation."
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "format": "json",
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if resp.status_code == 404:
        models = get_available_ollama_models()
        if models:
            raise requests.RequestException(
                f"model '{model}' not found. Available: {', '.join(models)}"
            )
        else:
            raise requests.RequestException(f"model '{model}' not found.")
    resp.raise_for_status()
    return _parse_llm_response(resp.json()["message"]["content"])


def _parse_llm_response(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()
    return json.loads(raw)


def write_log_entry(entry: str) -> None:
    log_path = WIKI_DIR / "log.md"
    content = log_path.read_text()
    if not content.endswith("\n"):
        content += "\n"
    content += "\n" + entry.strip() + "\n"
    log_path.write_text(content)


def write_new_page(rel_path: str, content: str) -> None:
    target = (WIKI_DIR / rel_path).resolve()
    if not str(target).startswith(str(WIKI_DIR.resolve())):
        print(f"  [auto-wiki] ERROR: path traversal attempt: {rel_path}", file=sys.stderr)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if not content.endswith("\n"):
        content += "\n"
    target.write_text(content)
    print(f"  [auto-wiki] created wiki/{rel_path}", file=sys.stderr)


def add_index_entries(entries: list[dict]) -> None:
    index_path = WIKI_DIR / "index.md"
    content = index_path.read_text()
    lines = content.split("\n")

    for entry in entries:
        section = entry.get("section", "")
        line = entry.get("entry", "")
        if not line:
            continue

        # Find the section header and insert after it
        section_header = f"## {section}"
        inserted = False
        new_lines = []
        i = 0
        while i < len(lines):
            new_lines.append(lines[i])
            if lines[i].strip() == section_header:
                # Find the insertion point — after the section header but before
                # any existing entries or next section
                insert_idx = i + 1
                # Skip past blank lines
                while insert_idx < len(lines) and lines[insert_idx].strip() == "":
                    new_lines.append(lines[insert_idx])
                    insert_idx += 1
                    i += 1
                # Insert the new entry if it's not already present
                if line.strip() not in "\n".join(lines):
                    new_lines.append(line)
                    inserted = True
                # Advance past the lines we just processed
                i = insert_idx - 1
            i += 1

        if inserted:
            lines = new_lines
            print(f"  [auto-wiki] index.md: added to {section}", file=sys.stderr)
        else:
            print(f"  [auto-wiki] index.md: could not find section '{section}' or entry already exists", file=sys.stderr)

    if new_lines:
        index_path.write_text("\n".join(new_lines))


def format_date_for_log() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


def main():
    parser = argparse.ArgumentParser(description="Auto-document staged changes in wiki")
    parser.add_argument(
        "--diff-file",
        required=True,
        help="Path to file containing git diff --cached output",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("WIKI_DOC_MODEL", DEFAULT_MODEL),
        help=f"OpenRouter model (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--ollama-model",
        default=os.getenv("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        help=f"Ollama fallback model (default: {DEFAULT_OLLAMA_MODEL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be done but don't write files",
    )
    args = parser.parse_args()

    diff_path = Path(args.diff_file)
    if not diff_path.is_file():
        print(f"  [auto-wiki] diff file not found: {args.diff_file}", file=sys.stderr)
        sys.exit(0)

    diff_content = diff_path.read_text()
    if not diff_content.strip():
        print("  [auto-wiki] no staged diff to analyze", file=sys.stderr)
        sys.exit(0)

    wiki_context = collect_wiki_context()

    prompt = f"""Analyze this git diff and determine what wiki documentation is needed.

=== Wiki Context ===

{wiki_context}

=== Staged Diff ===

{diff_content}
"""

    api_key = get_api_key()
    result = None

    # Try OpenRouter first
    if api_key:
        model = args.model
        print(f"  [auto-wiki] using OpenRouter model: {model}", file=sys.stderr)
        try:
            result = call_openrouter(prompt, model, api_key)
        except requests.RequestException as e:
            print(f"  [auto-wiki] OpenRouter error: {e}", file=sys.stderr)
            print("  [auto-wiki] falling back to ollama...", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"  [auto-wiki] failed to parse OpenRouter response: {e}", file=sys.stderr)
            print("  [auto-wiki] falling back to ollama...", file=sys.stderr)
    else:
        print("  [auto-wiki] no OPENROUTER_API_KEY found (env or keychain)", file=sys.stderr)
        print("  [auto-wiki] trying ollama...", file=sys.stderr)

    # Fallback to ollama
    if result is None:
        try:
            result = call_ollama(prompt, args.ollama_model)
            print(f"  [auto-wiki] ollama ({args.ollama_model}) succeeded", file=sys.stderr)
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"  [auto-wiki] ollama error: {e}", file=sys.stderr)
            print("  [auto-wiki] ERROR: No LLM (OpenRouter or Ollama) configured or available. Documentation is required.", file=sys.stderr)
            sys.exit(1)  # BLOCK the commit

    if not result or not result.get("should_update"):
        print("  [auto-wiki] no wiki changes needed", file=sys.stderr)
        sys.exit(0)

    print("  [auto-wiki] generating wiki documentation...", file=sys.stderr)

    if args.dry_run:
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # Write changes
    today = format_date_for_log()

    log_entry = result.get("log_entry", "")
    if log_entry:
        # Replace placeholder date with actual date
        log_entry = re.sub(r"## \[\d{4}-\d{2}-\d{2}\]", f"## [{today}]", log_entry)
        write_log_entry(log_entry)
        print("  [auto-wiki] appended to log.md", file=sys.stderr)

    for page in result.get("new_pages", []):
        path = page.get("path", "")
        content = page.get("content", "")
        if path and content:
            write_new_page(path, content)

    index_additions = result.get("index_additions", [])
    if index_additions:
        add_index_entries(index_additions)

    print("  [auto-wiki] done", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
