"""Post-validation for researcher-proposed prompts.

The researcher's `program.md` describes what NOT to do, but nothing prevents
the model from violating those rules. This module uses a two-tier approach:

- **Hard invariants**: Forbidden patterns, empty/oversized prompts. These
  BLOCK activation — they would break the trading loop's safety contract.
- **Soft invariants**: Tool usage requirements, 5 Whys technique. These
  emit WARNINGS but allow activation — the control portfolios and safety
  checker provide the real guardrails.
"""

from __future__ import annotations

import re

MAX_WORDS = 3000

# Hard invariants — block activation.
# Only things that would actually break the trading loop.
_HARD_INVARIANTS = (
    re.compile(r"ignore\s+verification\s+feedback", re.IGNORECASE),
    re.compile(r"bypass\s+system\s+guardrails", re.IGNORECASE),
    re.compile(r"skip\s+tool\s+use", re.IGNORECASE),
    re.compile(r"ignore\s+portfolio\s+limits", re.IGNORECASE),
    re.compile(r"guess\s+the\s+price", re.IGNORECASE),
)

# Soft invariants — warn but allow.
# Nice-to-have reasoning/quality features. The control portfolios
# benchmark these, so the researcher should be free to experiment.
_SOFT_INVARIANTS = (
    "calculate_buy_quantity",
    "calculate_sell_quantity",
    "5 Whys",
)


def validate_prompt(prompt: str) -> tuple[bool, str, list[str]]:
    """Validate a researcher-proposed prompt.

    Returns (is_valid, error_reason, warnings) where:
    - is_valid: False if a hard invariant is violated (block activation)
    - error_reason: reason for rejection (empty string if valid)
    - warnings: list of soft invariant violations (informational only)
    """
    warnings: list[str] = []

    if not prompt or not prompt.strip():
        return False, "Prompt is empty", warnings

    word_count = len(prompt.split())
    if word_count > MAX_WORDS:
        return False, f"Prompt exceeds maximum length ({word_count} words > {MAX_WORDS})", warnings

    for pattern in _HARD_INVARIANTS:
        match = pattern.search(prompt)
        if match:
            return False, f"Prompt contains forbidden phrase: {match.group(0)!r}", warnings

    for token in _SOFT_INVARIANTS:
        if token not in prompt:
            warnings.append(f"Prompt is missing recommended token: {token!r}")

    return True, "", warnings
