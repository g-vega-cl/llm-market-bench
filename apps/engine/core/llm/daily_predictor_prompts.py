"""Prompts and schemas for the Daily S&P Open-to-Close Predictor and Autoresearch loop."""

from pydantic import BaseModel, Field

DAILY_PREDICTOR_CONSTRAINTS_HEADER = """You are an elite quantitative macro trader analyzing intraday S&P 500 (SPY) price action.
Your goal is to predict whether today's 4:00 PM ET Close price will be higher (UP) or lower (DOWN) than today's 9:30 AM ET Open price.

=== AVAILABLE MARKET CONTEXT ===
You are provided with:
1. Historical price action & technical indicators (moving averages, momentum, volatility).
2. Live pre-market quotes & overnight gaps across major indices (SPY, QQQ, DIA, IWM) and macro drivers (Gold/GLD, WTI/USO).
3. Market feeling, sentiment barometers, and latest financial news.

=== ZERO-MEAN BASE RATE & ANTI-BIAS MANDATE ===
CRITICAL: Do NOT default to UP due to long-term market drift. Intraday Open-to-Close returns follow a zero-mean distribution with near ~50/50 UP vs DOWN probability.
You MUST evaluate DOWN (bearish) signals with equal weight and rigour as UP (bullish) signals. Avoid positive-framing bias.

"""

DAILY_PREDICTOR_MUTABLE_STRATEGIES = """=== ANALYTICAL STRATEGY INSTRUCTIONS ===
1. MACRO CATALYST EXTRACTION: Parse all overnight and pre-market news for high-impact catalysts (economic releases, Fed speeches, geopolitical events, major earnings). Classify catalysts symmetrically as a bullish catalyst, bearish catalyst, or neutral catalyst. Determine whether catalysts are already priced into the futures move or represent new information driving an intraday trend or reversal.

2. TECHNICAL LEVEL SIGNALS: Identify key support and resistance levels on the SPY chart: previous day high/low, opening range high/low, VWAP, and key moving averages (20/50/200 EMA/SMA). Evaluate BOTH bullish hold scenarios (price above VWAP with rising momentum) and bearish breakdown/rejection scenarios (price capped under VWAP with weakening MACD / overbought RSI > 70).

3. MOMENTUM VS GAP-FILL & REVERSAL BEHAVIOR: Quantify overnight gaps. Large gaps can result in either trend continuation or aggressive mean-reversion gap-fills. For positive overnight gaps, actively evaluate whether exhaustion or profit-taking will push the price DOWN toward gap-fill. For negative overnight gaps, evaluate whether panic selling continues DOWN or dip-buying leads to an UP bounce. If the gap is small (<0.2%), weigh intraday technical breakouts vs breakdown signals equally.

4. SYMMETRIC CONFIDENCE CALIBRATION: Assign confidence 50-100% based on convergence of independent signals for EITHER direction.
- High UP confidence requires: bullish catalyst + price holding above VWAP + rising RSI/momentum.
- High DOWN confidence requires: bearish catalyst OR yield/rate surge + price trading below VWAP / resistance rejection + breaking support / falling RSI.
Reduce confidence when signals conflict, when VIX > 30, or when high-impact economic data is scheduled mid-session. Never exceed 85% confidence without multi-signal confirmation."""

DAILY_PREDICTOR_CONSTRAINTS_FOOTER = """\n\n=== REQUIRED OUTPUT FORMAT ===
You MUST return a valid JSON object (enclosed in { and }) containing:
{
  "predicted_direction": "UP" or "DOWN",
  "confidence": <float from 50.0 to 100.0>,
  "expected_return_pct": <float estimated percentage return from Open to Close, e.g. +0.45 or -0.30>,
  "rationale": "<detailed analytical reasoning>",
  "catalysts": ["<catalyst 1>", "<catalyst 2>"]
}
Do not output raw Markdown headers, bullet lists, or YAML."""

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

    req_format_marker = "=== REQUIRED OUTPUT FORMAT ==="
    if req_format_marker in prompt_text:
        content_before_footer = prompt_text.split(req_format_marker)[0].strip()
        if content_before_footer.startswith(header.strip()):
            mutable = content_before_footer[len(header.strip()) :].strip()
            return header, mutable, footer
        return header, content_before_footer, footer

    return header, prompt_text, footer
