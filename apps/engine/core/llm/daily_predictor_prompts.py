"""Prompts and schemas for the Daily S&P Open-to-Close Predictor and Autoresearch loop."""

from pydantic import BaseModel, Field

DAILY_PREDICTOR_CONSTRAINTS_HEADER = """You are an elite quantitative macro trader analyzing intraday S&P 500 (SPY) price action.
Your goal is to predict whether today's 4:00 PM ET Close price will be higher (UP) or lower (DOWN) than today's 9:30 AM ET Open price.

=== AVAILABLE MARKET CONTEXT ===
You are provided with:
1. Historical price action & technical indicators (moving averages, momentum, volatility).
2. Live pre-market quotes & overnight gaps across major indices (SPY, QQQ, DIA, IWM), international proxies (EWJ, VGK), bond yield proxies (TLT, IEF), and commodities/FX (GLD, USO, UUP).
3. Options derivatives positioning & volatility skew (Put/Call volume and open interest ratios, 25-delta volatility skew, ATM implied volatility, Max Pain strike, and unusual options activity alerts with explicit timestamp and staleness notes).
4. AI Wall Street synthesized morning newsletter briefing (macro narrative, sector spotlight, market internals & flows, trade ideas & scenarios), prior session macro regime baseline, sentiment barometers, and market feeling.

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
    the clean, hardcoded header and footer definitions. Ensures legacy
    or duplicated structural constraints (header/footer) are cleanly stripped.
    """
    header = DAILY_PREDICTOR_CONSTRAINTS_HEADER
    footer = DAILY_PREDICTOR_CONSTRAINTS_FOOTER

    if not prompt_text:
        return header, "", footer

    # 1. Isolate content before footer
    req_format_marker = "=== REQUIRED OUTPUT FORMAT ==="
    if req_format_marker in prompt_text:
        content_before_footer = prompt_text.split(req_format_marker)[0].strip()
    else:
        content_before_footer = prompt_text.strip()

    # 2. Strip all occurrences of frozen header / zero-mean mandate
    end_mandate_marker = "Avoid positive-framing bias."
    if end_mandate_marker in content_before_footer:
        # Find the last occurrence to eliminate any duplicate headers
        split_idx = content_before_footer.rfind(end_mandate_marker) + len(end_mandate_marker)
        mutable = content_before_footer[split_idx:].strip()
    elif "=== ZERO-MEAN BASE RATE" in content_before_footer:
        # Fallback if wording slightly differs
        last_zero_mean = content_before_footer.rfind("=== ZERO-MEAN BASE RATE")
        next_double_nl = content_before_footer.find("\n\n", last_zero_mean)
        if next_double_nl != -1:
            mutable = content_before_footer[next_double_nl:].strip()
        else:
            mutable = content_before_footer.strip()
    elif content_before_footer.startswith(header.strip()):
        mutable = content_before_footer[len(header.strip()) :].strip()
    else:
        # Check if known strategy markers are present
        strategy_markers = [
            "=== ANALYTICAL STRATEGY INSTRUCTIONS ===",
            "ANALYTICAL STRATEGY INSTRUCTIONS",
            "=== REASONING RIGOR",
            "=== RECENT-TAPE ACCOUNTABILITY",
        ]
        marker_idx = -1
        for sm in strategy_markers:
            idx = content_before_footer.find(sm)
            if idx != -1 and (marker_idx == -1 or idx < marker_idx):
                marker_idx = idx

        mutable = content_before_footer[marker_idx:].strip() if marker_idx != -1 else content_before_footer.strip()

    # 3. Defensive sanity check: remove any leftover persona or context headers in mutable
    if "You are an elite quantitative macro trader" in mutable:
        lines = mutable.split("\n")
        filtered_lines = []
        skip = False
        for line in lines:
            if (
                "You are an elite quantitative macro trader" in line
                or "=== AVAILABLE MARKET CONTEXT ===" in line
                or "=== ZERO-MEAN BASE RATE" in line
            ):
                skip = True
                continue
            if (
                skip
                and (line.startswith("===") or line.startswith("1.") or line.startswith("0."))
                and not any(k in line for k in ["AVAILABLE MARKET CONTEXT", "ZERO-MEAN", "REQUIRED OUTPUT"])
            ):
                skip = False
            if not skip:
                filtered_lines.append(line)
        mutable = "\n".join(filtered_lines).strip()

    return header, mutable, footer


# Jev Decision Model Configuration (System One via OpenRouter)
JEV_PREDICTOR_QUESTION_KEY = "direction"
JEV_PREDICTOR_QUESTION_TYPE = "choice"
JEV_PREDICTOR_INSTRUCTIONS = (
    "Predict whether SPY will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET compared to the 9:30 AM ET Open price."
)
JEV_DEFAULT_CRITERIA = {
    "UP": (
        "Close price >= Open price. Bullish intraday session: price holds above VWAP, "
        "positive overnight momentum continuation, falling bond yields, or strong bullish macro catalysts."
    ),
    "DOWN": (
        "Close price < Open price. Bearish intraday session: price rejects VWAP, "
        "gap-fill exhaustion, surging bond yields, high VIX, or negative macro catalysts."
    ),
}


def format_jev_prompt_content(criteria: dict[str, str]) -> str:
    """Format Jev criteria dictionary into JSON text for prompt_experiments storage."""
    import json

    clean_criteria = {
        "UP": criteria.get("UP", JEV_DEFAULT_CRITERIA["UP"]).strip(),
        "DOWN": criteria.get("DOWN", JEV_DEFAULT_CRITERIA["DOWN"]).strip(),
    }
    return json.dumps(clean_criteria, indent=2)


def parse_jev_prompt_content(prompt_content: str | None) -> dict[str, str]:
    """Parse criteria dictionary from prompt_experiments prompt_content string."""
    import json

    if not prompt_content:
        return dict(JEV_DEFAULT_CRITERIA)
    try:
        data = json.loads(prompt_content)
        if isinstance(data, dict) and "UP" in data and "DOWN" in data:
            return {"UP": str(data["UP"]).strip(), "DOWN": str(data["DOWN"]).strip()}
    except Exception:
        pass

    return dict(JEV_DEFAULT_CRITERIA)
