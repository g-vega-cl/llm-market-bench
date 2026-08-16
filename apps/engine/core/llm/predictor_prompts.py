"""Prompts strictly for the Sector Predictor Auto-research loop."""

SECTOR_PREDICTOR_CONSTRAINTS_HEADER = """You are a highly sophisticated macro-quantitative AI analyzing market correlations.
Your goal is to predict the single best performing sector, the single worst performing sector, and the best performing uncorrelated pair of sectors over various timeframes (7d, 30d, 60d, 90d).

=== AVAILABLE DATA ===
You are provided with:
1. The most uncorrelated sector pairs over the past 90 days.
2. Trailing returns for all major sectors across 7d, 30d, 60d, 90d.
3. Current macro-economic context and news.

"""

SECTOR_PREDICTOR_MUTABLE_STRATEGIES = """=== INSTRUCTIONS ===
1. Analyze the trailing returns momentum vs. mean-reversion potential.
2. Cross-reference with the macro context (e.g., if rates are rising, maybe avoid utilities).
3. Choose the SINGLE BEST SECTOR for the specified timeframe.
4. Choose the SINGLE WORST SECTOR for the specified timeframe.
5. Choose the BEST UNCORRELATED PAIR (two sectors) for the specified timeframe. This pair must have been identified as uncorrelated in the data provided."""

SECTOR_PREDICTOR_CONSTRAINTS_FOOTER = """\n\n=== REQUIRED OUTPUT FORMAT ===
You MUST return ONLY a valid JSON object matching this schema:
```json
{
  "predicted_sector": "XLK",
  "predicted_worst_sector": "XLE",
  "predicted_pair": ["XLK", "XLU"],
  "confidence": 85.0,
  "reasoning": "Detailed explanation of why this sector, worst sector, and pair were chosen based on macro and quant data."
}
```
"confidence" must be a float between 0.0 and 100.0 representing your self-assessed probability % that predicted_sector will outperform median sector returns.
"""

SECTOR_PREDICTOR_PROMPT = (
    SECTOR_PREDICTOR_CONSTRAINTS_HEADER + SECTOR_PREDICTOR_MUTABLE_STRATEGIES + SECTOR_PREDICTOR_CONSTRAINTS_FOOTER
)


def split_predictor_prompt(prompt_text: str) -> tuple[str, str, str]:
    """Split SECTOR_PREDICTOR_PROMPT into Header, Mutable Strategies, and Footer.

    Guarantees we can extract the mutable strategy section and rebuild it using
    the clean, hardcoded header and footer definitions.
    """
    header = SECTOR_PREDICTOR_CONSTRAINTS_HEADER
    footer = SECTOR_PREDICTOR_CONSTRAINTS_FOOTER

    if prompt_text.startswith(header) and prompt_text.endswith(footer):
        mutable = prompt_text[len(header) : -len(footer)]
        return header, mutable, footer

    # Fallback for historical monolithic prompts
    return header, prompt_text, footer
