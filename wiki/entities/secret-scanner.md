---
tags: [security, secrets, pre-commit, linting, tooling]
category: entity
---

# Secret Scanner

`apps/engine/secret_scanner.py` is a hermetic, dependency-free pre-commit guard that scans staged git diffs (and, optionally, arbitrary files) for leaked API keys and credentials. It is the enforcement arm of [[concepts/env-based-secrets]]: the rule is that no secret value may appear in a tracked file, and this script fails the commit when one does.

## Where It Runs

1. **Pre-commit hook** — `.husky/pre-commit` invokes it as the very first step, before auto-wiki, linters, tests, and the web build:
   ```sh
   "$REPO_ROOT/apps/engine/.venv/bin/python3" "$REPO_ROOT/apps/engine/secret_scanner.py" --cached || exit 1
   ```
   It is fail-fast and blocking — a finding aborts the commit immediately.
2. **Structural wiki lint** — `apps/engine/wiki_lint.py` imports `scan_text` and runs it over every wiki page body, emitting `[leaked-secret]` issues (see [[entities/wiki-linter]]). This catches keys pasted into documentation, which the pre-commit diff scan would also catch but the wiki lint surfaces as a lint finding.

## Detection Rules

`SECRET_PATTERNS` is an ordered list of `(rule_name, compiled_regex)` pairs with explicit length boundaries to avoid matching short placeholder fragments:

| Rule | Pattern |
| :--- | :--- |
| Free Proxy Master Key | `sk-free-[a-f0-9]{24,}` |
| Groq API Key | `gsk_[a-zA-Z0-9]{20,}` |
| Google Gemini API Key | `AIzaSy[a-zA-Z0-9_-]{33}` |
| Google Generative Key | `AQ\.[a-zA-Z0-9_-]{40,}` |
| OpenRouter API Key | `sk-or-v1-[a-f0-9]{32,}` |
| NVIDIA NIM API Key | `nvapi-[a-zA-Z0-9_-]{30,}` |
| GitHub Personal Access Token | `ghp_[a-zA-Z0-9]{36}` |
| Generic Bearer Secret | `sk-[a-zA-Z0-9]{32,}` |

## Allowlist & Exemptions

`ALLOWLIST_SUBSTRINGS` suppresses false positives on documentation and fixtures. A line (or a matched value) containing any of these tokens is skipped:

`<`, `>`, `...`, `example`, `placeholder`, `secret-key-12345`, `mock-`, `test-master-key`, `gemini_test_key`, `gsk_test_key`, `or_test_key`

`EXEMPT_FILE_SUFFIXES` skips whole files by path suffix: `.env.example`, `.dockerignore`, `.gitignore`, and `test_secret_scanner.py` (the scanner's own test suite, which necessarily contains synthetic key-shaped literals).

## Scanning Modes

- **`--cached`** (default) — `scan_git_cached()` runs `git diff --cached -U0`, tracks the current file from `+++ b/<path>` headers, and scans only added (`+`) lines. Removed (`-`) lines are ignored so deleting a leaked key never re-triggers the alarm.
- **Explicit paths** — `secret_scanner.py path/to/file.md ...` reads each file and scans its full text via `scan_file_content()`.
- **No arguments** — falls back to `--cached`.

## Output & Exit Codes

On findings the script prints a `🚨 [SECURITY ALERT]` block to stderr listing `file:line -> [rule] matched: <masked>` for each hit, where the matched value is masked to its first 8 and last 4 characters (or `***` when shorter than 12 characters) so the terminal never echoes the full secret. It returns exit code `1`. A clean scan returns `0` silently.

## Tests

`apps/engine/tests/test_secret_scanner.py` is fully hermetic and covers detection of each signature family, placeholder allowlisting, `.env.example` exemption, direct file scanning, staged-diff scanning (with `subprocess.run` monkeypatched), and both CLI exit paths.

## Related

- [[concepts/env-based-secrets]] — the secret-handling rule this scanner enforces
- [[concepts/project-linting]] — pre-commit hook ordering
- [[entities/wiki-linter]] — structural lint that also runs the scanner over wiki pages
- [[entities/rotate-secrets]] — rotation utility for when a key does leak
