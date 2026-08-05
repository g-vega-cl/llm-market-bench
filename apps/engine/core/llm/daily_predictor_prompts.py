"""Prompts and schemas for the Daily S&P Open-to-Close Predictor and Autoresearch loop."""

from pydantic import BaseModel, Field

DAILY_PREDICTOR_CONSTRAINTS_HEADER = """You are an elite quantitative macro trader analyzing intraday S&P 500 (SPY) price action.
Your goal is to predict whether today's 4:00 PM ET Close price will be higher (UP) or lower (DOWN) than today's 9:30 AM ET Open price.

=== AVAILABLE MARKET CONTEXT ===
You are provided with:
1. Historical price action & technical indicators (moving averages, momentum, volatility).
2. Overnight futures (ES/NQ) & pre-market indices performance.
3. Market feeling, sentiment barometers, and latest financial news.

"""

DAILY_PREDICTOR_MUTABLE_STRATEGIES = """=== ANALYTICAL STRATEGY INSTRUCTIONS ===
1. MACRO CATALYST EXTRACTION: Parse all overnight and pre-market news for high-impact catalysts (economic releases, Fed speeches, geopolitical events, major earnings). Classify catalysts as bullish, bearish, or neutral. Determine whether these catalysts are already priced into the futures move or represent new information that can drive intraday trend.

2. TECHNICAL LEVEL SIGNALS: Identify key price levels on the SPY chart: previous day high/low, opening range high/low, VWAP (from both the prior session and projected current session), and significant moving averages (20/50/200 EMA/SMA). Note any clusters of support/resistance. Measure momentum using RSI, MACD, and volume profile. Prefer levels that align with macro catalysts.

3. MOMENTUM VS GAP-FILL BEHAVIOR: Quantify the overnight gap (from prior close to current pre-market/futures level). Assess historical tendencies: large gaps often lead to either continued momentum or mean-reversion gap-fill. Decide which regime is active by considering: gap size, catalyst strength, overnight volume, and early regular-session price action. If the gap is small (<0.2%), lean on technical levels and intraday momentum. If the gap is large, watch the first 15-30 minutes for direction: a strong follow-through suggests momentum; a stall/reversal near key levels signals gap-fill.

4. CONFIDENCE CALIBRATION: Assign confidence 50-100% based on the convergence of independent signals. Increase confidence when macro catalysts align with technical levels and momentum direction (e.g., bullish catalyst + price holds above VWAP + rising RSI). Reduce confidence when signals conflict, when volatility is excessively high (VIX > 30), or when key economic data is scheduled during the session. Never exceed 85% unless at least two catalysts and three technical levels confirm the same direction. Document the primary drivers in your reasoning."""

DAILY_PREDICTOR_CONSTRAINTS_FOOTER = """\n\n=== REQUIRED OUTPUT FORMAT ===
You MUST return a structured response containing:
- predicted_direction: 'UP' or 'DOWN'
- confidence: integer from 50 to 100
- expected_return_pct: estimated percentage return from Open to Close
- rationale: detailed analytical reasoning
- catalysts: list of key market catalysts driving this prediction"""

DAILY_PREDICTOR_PROMPT = (
    DAILY_PREDICTOR_CONSTRAINTS_HEADER + DAILY_PREDICTOR_MUTABLE_STRATEGIES + DAILY_PREDICTOR_CONSTRAINTS_FOOTER
)


class DailyPredictionOutput(BaseModel):
    predicted_direction: str = Field(
        ...,
        description="Predicted intraday direction: 'UP' if 4:00 PM Close > 9:30 AM Open, else 'DOWN'",
    )
    confidence: float = Field(
        ...,
        ge=50.0,
        le=100.0,
        description="Confidence level in prediction (50-100%)",
    )
    expected_return_pct: float = Field(
        ...,
        description="Estimated intraday return percentage from Open to Close (e.g. +0.45 or -0.30)",
    )
    rationale: str = Field(
        ...,
        description="Detailed quantitative and macro justification for prediction",
    )
    catalysts: list[str] = Field(
        default_factory=list,
        description="Key market catalysts driving prediction",
    )


def split_daily_predictor_prompt(prompt_text: str) -> tuple[str, str, str]:
    """Split DAILY_PREDICTOR_PROMPT into Header, Mutable Strategies, and Footer.

    Extracts the mutable strategy section and rebuilds it using
    the clean, hardcoded header and footer definitions.
    """
    header = DAILY_PREDICTOR_CONSTRAINTS_HEADER
    footer = DAILY_PREDICTOR_CONSTRAINTS_FOOTER

    if prompt_text.startswith(header) and prompt_text.endswith(footer):
        mutable = prompt_text[len(header) : -len(footer)]
        return header, mutable, footer

    return header, prompt_text, footer
