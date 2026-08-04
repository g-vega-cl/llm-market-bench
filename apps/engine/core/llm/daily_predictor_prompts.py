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
1. Evaluate overnight news and futures direction vs. regular session gap risk.
2. Examine key technical levels (support/resistance, VWAP trends, momentum signals).
3. Synthesize macro sentiment and catalyst impact to assess intraday direction.
4. Output a clear directional prediction (UP or DOWN) along with a calibrated confidence score (50-100%)."""

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
