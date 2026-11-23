"""Frozen and mutable sections for the TLT bond-predictor prompt.

The frozen header/footer are managed in code; only the mutable strategy block is
rewritten by the weekly bond autoresearch loop (see `tasks/bond_autoresearch.py`).
"""

BOND_PREDICTOR_PROMPT_NAME = "BOND_PREDICTOR_PROMPT"

BOND_PREDICTOR_CONSTRAINTS_HEADER = """You are an elite fixed-income quantitative strategist predicting open-to-close price direction for the 20+ Year Treasury Bond ETF (TLT).

Fixed Income Mechanics:
- Bond prices move inversely to Treasury yields. Falling yields = TLT UP; Rising yields = TLT DOWN.
- High duration (~17 years) makes TLT sensitive to morning economic prints (CPI, PPI, Jobs, NFP), Fed expectations, and Treasury auction tails.
- Use your callable tools autonomously to inspect the Treasury yield curve, today's scheduled economic releases, options sentiment, and calendar triggers.
- Formulate an objective, unbiased conviction on whether TLT will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET compared to 9:30 AM ET open.
"""

BOND_PREDICTOR_MUTABLE_STRATEGIES = """=== BASELINE BOND STRATEGY ===
1. Anchor on the highest-conviction driver first: a scheduled macro print today or a decisive move in the Treasury yield curve.
2. Require at least two independent confirmations (yield-curve regime, options sentiment, calendar scenario) before committing to a direction.
3. Prefer UP when yields are falling or the market is pricing a dovish repricing; prefer DOWN when yields are rising into supply or on hawkish data.
4. Scale confidence with the number of confirming signals, and keep it inside the 50-100 range.
"""

BOND_PREDICTOR_CONSTRAINTS_FOOTER = """

=== REQUIRED OUTPUT ===
Return predicted_direction (UP or DOWN), confidence (50-100), expected_return_pct, rationale, and catalysts.
"""

BOND_PREDICTOR_PROMPT = (
    BOND_PREDICTOR_CONSTRAINTS_HEADER + BOND_PREDICTOR_MUTABLE_STRATEGIES + BOND_PREDICTOR_CONSTRAINTS_FOOTER
)


def split_bond_prompt(prompt_text: str) -> tuple[str, str, str]:
    """Split a bond prompt into (frozen header, mutable strategy, frozen footer).

    Falls back to the code-owned header/footer when the stored prompt does not
    carry the expected sections, so a malformed variant cannot drop the frozen
    constraints.
    """
    if prompt_text.startswith(BOND_PREDICTOR_CONSTRAINTS_HEADER) and prompt_text.endswith(
        BOND_PREDICTOR_CONSTRAINTS_FOOTER
    ):
        mutable = prompt_text[len(BOND_PREDICTOR_CONSTRAINTS_HEADER) : -len(BOND_PREDICTOR_CONSTRAINTS_FOOTER)]
        return BOND_PREDICTOR_CONSTRAINTS_HEADER, mutable, BOND_PREDICTOR_CONSTRAINTS_FOOTER

    if prompt_text.startswith(BOND_PREDICTOR_CONSTRAINTS_HEADER):
        mutable = prompt_text[len(BOND_PREDICTOR_CONSTRAINTS_HEADER) :]
        return BOND_PREDICTOR_CONSTRAINTS_HEADER, mutable, BOND_PREDICTOR_CONSTRAINTS_FOOTER

    return BOND_PREDICTOR_CONSTRAINTS_HEADER, prompt_text, BOND_PREDICTOR_CONSTRAINTS_FOOTER
