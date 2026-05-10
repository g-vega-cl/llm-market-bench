"""Post-validation for researcher-proposed prompts.

The researcher's `program.md` describes what NOT to do, but nothing prevents
the model from violating those rules. This module rejects any prompt that
would weaken the trading-loop safety contract before we activate it.
"""

from __future__ import annotations

import re

MAX_WORDS = 3000

_REQUIRED_TOKENS = (
    "calculate_buy_quantity",
    "calculate_sell_quantity",
    "5 Whys",
)

_FORBIDDEN_PATTERNS = (
    re.compile(r"ignore\s+verification\s+feedback", re.IGNORECASE),
    re.compile(r"bypass\s+system\s+guardrails", re.IGNORECASE),
    re.compile(r"skip\s+tool\s+use", re.IGNORECASE),
    re.compile(r"ignore\s+portfolio\s+limits", re.IGNORECASE),
    re.compile(r"guess\s+the\s+price", re.IGNORECASE),
)


def validate_prompt(prompt: str) -> tuple[bool, str]:
    """Validate a researcher-proposed prompt.

    Returns (True, "") if the prompt is safe to activate, otherwise
    (False, reason). The trading loop's safety invariants are encoded here.
    """
    if not prompt or not prompt.strip():
        return False, "Prompt is empty"

    word_count = len(prompt.split())
    if word_count > MAX_WORDS:
        return False, f"Prompt exceeds maximum length ({word_count} words > {MAX_WORDS})"

    for token in _REQUIRED_TOKENS:
        if token not in prompt:
            return False, f"Prompt is missing required token: {token!r}"

    for pattern in _FORBIDDEN_PATTERNS:
        match = pattern.search(prompt)
        if match:
            return False, f"Prompt contains forbidden phrase: {match.group(0)!r}"

    return True, ""
