from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

STOCK_PICKER_CONSTRAINTS_HEADER = """You are an elite quantitative equity analyst and long/short portfolio manager.
Your task is to analyze today's candidate stocks and select exactly 3 stocks poised to go UP (Long) and 3 stocks poised to go DOWN (Short) during today's Regular Trading Hours (09:30 AM to 04:00 PM ET).

=== MISSION & RULES ===
1. You are provided with a curated candidate pool of stocks actively moving in pre-market or highlighted in that morning's intelligence briefing.
2. You MUST select EXACTLY 3 unique stocks for UP (ranked 1, 2, 3) and EXACTLY 3 unique stocks for DOWN (ranked 1, 2, 3).
3. NO DUPLICATE TICKERS: A ticker chosen for UP cannot be chosen for DOWN, and no ticker may appear more than once. All 6 selected tickers must be distinct and chosen from the candidate pool.
4. CONFIDENCE BOUNDS: Every pick must carry an individual conviction confidence score between 50.0% and 100.0%.
5. TARGET TIMEFRAME: Intraday performance from 09:30 AM ET Open to 04:00 PM ET Close.

"""

STOCK_PICKER_MUTABLE_STRATEGIES = """=== LONG/SHORT RELATIVE SELECTION STRATEGY ===
1. UP PICKS (RELATIVE STRENGTH & CATALYST DRIVERS):
- Identify assets with positive expectation gaps: earnings beats with raised guidance, contract/patent awards, or high-conviction thematic tailwinds (AI infrastructure, electrification, pricing power).
- Look for pre-market volume surges holding above prior-day resistance levels.
- Prioritize companies capable of outperforming the broad market even in a neutral or choppy macro tape.

2. DOWN PICKS (RELATIVE WEAKNESS & MULTIPLE COMPRESSION):
- Identify assets with asymmetric downside risk: slowing guidance, margin compression, high debt refinance risk under elevated yields, or extreme speculative multiples vulnerable to mean-reversion.
- Look for failed gap-ups, distribution patterns below key moving averages, or adverse consumer/regulatory headwinds.
- Prioritize high-beta long-duration laggards vulnerable to discount-rate expansion.

3. BALANCED BASKET CONSTRUCT:
- Avoid excessive single-industry concentration in the Long or Short basket unless a clear sector-rotation theme justifies it.
- Calibrate expected return magnitude (typically +/- 0.5% to 5.0% for intraday equities)."""

STOCK_PICKER_CONSTRAINTS_FOOTER = """\n\n=== REQUIRED OUTPUT FORMAT ===
You MUST return a valid JSON object matching the following structure:
{
  "picks_up": [
    {
      "ticker": "XYZ",
      "direction": "UP",
      "rank": 1,
      "confidence": 75.0,
      "expected_return_pct": 2.1,
      "reasoning": "Concise thesis explaining why this stock will outperform today."
    },
    ... (exactly 3 items for UP, ranks 1, 2, 3)
  ],
  "picks_down": [
    {
      "ticker": "ABC",
      "direction": "DOWN",
      "rank": 1,
      "confidence": 78.0,
      "expected_return_pct": -2.4,
      "reasoning": "Concise thesis explaining why this stock will underperform today."
    },
    ... (exactly 3 items for DOWN, ranks 1, 2, 3)
  ],
  "market_regime_rationale": "High-level summary of the macro backdrop driving your selections."
}
"""

STOCK_PICKER_PROMPT = (
    STOCK_PICKER_CONSTRAINTS_HEADER + STOCK_PICKER_MUTABLE_STRATEGIES + STOCK_PICKER_CONSTRAINTS_FOOTER
)


class StockPickItem(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol (uppercase)")
    direction: Literal["UP", "DOWN"] = Field(..., description="Direction: UP or DOWN")
    rank: int = Field(..., ge=1, le=3, description="Rank within direction: 1, 2, or 3")
    confidence: float = Field(..., ge=50.0, le=100.0, description="Conviction confidence score between 50.0 and 100.0")
    expected_return_pct: float | None = Field(default=None, description="Expected intraday return percentage")
    reasoning: str = Field(..., min_length=10, description="Concise analytical rationale for the pick")


class StockPickerOutput(BaseModel):
    picks_up: list[StockPickItem] = Field(
        ..., min_length=3, max_length=3, description="Top 3 stocks predicted to go UP"
    )
    picks_down: list[StockPickItem] = Field(
        ..., min_length=3, max_length=3, description="Top 3 stocks predicted to go DOWN"
    )
    market_regime_rationale: str = Field(default="", description="Macro regime summary influencing the basket")


def split_stock_picker_prompt(prompt_text: str) -> tuple[str, str, str]:
    """Splits a full stock picker prompt into (header, mutable_strategy, footer)."""
    header_marker = "=== LONG/SHORT RELATIVE SELECTION STRATEGY ==="
    footer_marker = "=== REQUIRED OUTPUT FORMAT ==="

    if header_marker in prompt_text and footer_marker in prompt_text:
        header_end = prompt_text.index(header_marker)
        header = prompt_text[:header_end].rstrip() + "\n\n"
        footer_start = prompt_text.index(footer_marker)
        mutable_body = prompt_text[header_end:footer_start].strip()
        footer = "\n\n" + prompt_text[footer_start:].lstrip()
        return header, mutable_body, footer

    # Fallback to defaults
    return (
        STOCK_PICKER_CONSTRAINTS_HEADER,
        STOCK_PICKER_MUTABLE_STRATEGIES,
        STOCK_PICKER_CONSTRAINTS_FOOTER,
    )
