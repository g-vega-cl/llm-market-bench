#!/usr/bin/env python3
"""Pre-commit secret scanner for detecting leaked API keys in staged files and markdown docs."""

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Explicit secret signatures with minimum length boundaries
SECRET_PATTERNS = [
    ("Free Proxy Master Key", re.compile(r"\bsk-free-[a-f0-9]{24,}\b", re.IGNORECASE)),
    ("Groq API Key", re.compile(r"\bgsk_[a-zA-Z0-9]{20,}\b")),
    ("Google Gemini API Key", re.compile(r"\bAIzaSy[a-zA-Z0-9_-]{33}\b")),
    ("Google Generative Key", re.compile(r"\bAQ\.[a-zA-Z0-9_-]{40,}\b")),
    ("OpenRouter API Key", re.compile(r"\bsk-or-v1-[a-f0-9]{32,}\b")),
    ("NVIDIA NIM API Key", re.compile(r"\bnvapi-[a-zA-Z0-9_-]{30,}\b")),
    ("GitHub Personal Access Token", re.compile(r"\bghp_[a-zA-Z0-9]{36}\b")),
    ("Generic Bearer Secret", re.compile(r"\bsk-[a-zA-Z0-9]{32,}\b")),
]

# Patterns or substrings that indicate legitimate examples or mock fixtures
ALLOWLIST_SUBSTRINGS = [
    "<",
    ">",
    "...",
    "example",
    "placeholder",
    "secret-key-12345",
    "mock-",
    "test-master-key",
    "gemini_test_key",
    "gsk_test_key",
    "or_test_key",
]

# Files or path patterns that are exempt from scanning
EXEMPT_FILE_SUFFIXES = [
    ".env.example",
    ".dockerignore",
    ".gitignore",
    "test_secret_scanner.py",
]


def is_file_exempt(filename: str) -> bool:
    """Returns True if the file path is explicitly exempt from secret checks."""
    fn_lower = filename.lower()
    return any(fn_lower.endswith(sfx) for sfx in EXEMPT_FILE_SUFFIXES)


def scan_text(text: str, filename: str = "staged") -> list[dict]:
    """Scans text content line-by-line against SECRET_PATTERNS."""
    if is_file_exempt(filename):
        return []

    findings = []
    for line_idx, line in enumerate(text.splitlines(), start=1):
        # Ignore deleted diff lines or lines with explicit placeholders
        if line.startswith("-") and not line.startswith("---"):
            continue

        stripped = line.strip()
        if any(token in stripped for token in ALLOWLIST_SUBSTRINGS):
            continue

        for rule_name, pattern in SECRET_PATTERNS:
            match = pattern.search(stripped)
            if match:
                matched_val = match.group(0)
                # Double check matched value against allowlist
                if any(token in matched_val for token in ALLOWLIST_SUBSTRINGS):
                    continue
                # Mask secret preview for safe terminal display
                masked = matched_val[:8] + "..." + matched_val[-4:] if len(matched_val) > 12 else "***"
                findings.append(
                    {
                        "file": filename,
                        "line": line_idx,
                        "rule": rule_name,
                        "masked": masked,
                    }
                )
    return findings


def scan_file_content(path: Path) -> list[dict]:
    """Reads a file and scans its text content."""
    if not path.is_file() or is_file_exempt(str(path)):
        return []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
        return scan_text(content, filename=str(path))
    except Exception:
        return []


def scan_git_cached() -> list[dict]:
    """Scans git staged diffs via git diff --cached."""
    try:
        proc = subprocess.run(
            ["git", "diff", "--cached", "-U0"],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as e:
        print(f"[secret-scanner] Warning: git diff failed: {e}", file=sys.stderr)
        return []

    diff_text = proc.stdout
    findings = []
    current_file = "staged"

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
            continue
        if line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            file_findings = scan_text(added_content, filename=current_file)
            findings.extend(file_findings)

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan files or staged diffs for leaked secrets.")
    parser.add_argument("--cached", action="store_true", help="Scan git staged diffs")
    parser.add_argument("files", nargs="*", help="Optional file paths to scan directly")
    args = parser.parse_args()

    findings = []
    if args.cached:
        findings.extend(scan_git_cached())
    elif args.files:
        for f in args.files:
            findings.extend(scan_file_content(Path(f)))
    else:
        # Default: scan git cached
        findings.extend(scan_git_cached())

    if findings:
        print("\n🚨 [SECURITY ALERT] Secrets or live API keys detected in staged changes!\n", file=sys.stderr)
        for item in findings:
            print(
                f"  • {item['file']}:{item['line']} -> [{item['rule']}] matched: {item['masked']}",
                file=sys.stderr,
            )
        print(
            "\nPlease remove the plaintext key, use environment variables, or replace with '<...>' placeholder.\n",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
