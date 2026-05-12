"""Post-validation for researcher-proposed prompts.

The researcher's `program.md` describes what NOT to do, but nothing prevents
the model from violating those rules. This module enforces hard invariants
(forbidden patterns, empty/oversized prompts) that BLOCK activation — they
would break the trading loop's safety contract.

There are no soft invariants or recommended tokens. The prompt is an
experiment space — the control portfolios and safety checker provide the
real guardrails, and hardcoded token requirements would only constrain
the researcher's ability to explore.
"""

from __future__ import annotations

import re

MAX_WORDS = 1000  # Conservative: ~1300 tokens for typical English (1.3 tok/word)


# Hard invariants — block activation.
# Only things that would actually break the trading loop.
_HARD_INVARIANTS = (
    re.compile(r"ignore\s+verification\s+feedback", re.IGNORECASE),
    re.compile(r"bypass\s+system\s+guardrails", re.IGNORECASE),
    re.compile(r"skip\s+tool\s+use", re.IGNORECASE),
    re.compile(r"ignore\s+portfolio\s+limits", re.IGNORECASE),
    re.compile(r"guess\s+the\s+price", re.IGNORECASE),
)


def _count_words(text: str) -> int:
    """Count words via split(). Conservative cap: 1000 words.
    English text averages ~1.3 tokens/word, so 1000 words ≈ 1300 tokens."""
    return len(text.split())


def validate_prompt(prompt: str) -> tuple[bool, str, list[str]]:
    """Validate a researcher-proposed prompt.

    Returns (is_valid, error_reason, warnings) where:
    - is_valid: False if a hard invariant is violated (block activation)
    - error_reason: reason for rejection (empty string if valid)
    - warnings: always empty list (kept for API compatibility)
    """
    warnings: list[str] = []

    if not prompt or not prompt.strip():
        return False, "Prompt is empty", warnings

    word_count = _count_words(prompt)
    if word_count > MAX_WORDS:
        return False, f"Prompt exceeds maximum length ({word_count} words > {MAX_WORDS})", warnings

    for pattern in _HARD_INVARIANTS:
        match = pattern.search(prompt)
        if match:
            return False, f"Prompt contains forbidden phrase: {match.group(0)!r}", warnings

    return True, "", warnings
