"""Prompt definitions, output schemas, and Jev criteria for Day-1 Earnings Movement Predictor."""

import json
from typing import Literal

from pydantic import BaseModel, Field


class EarningsPredictionOutput(BaseModel):
    """Structured response schema for LLM earnings movement predictions."""

    predicted_direction: Literal["UP", "DOWN"] = Field(
        ...,
        description="Predicted Day-1 price direction from 9:30 AM Open to 4:00 PM Close (UP or DOWN).",
    )
    confidence: float = Field(
        ...,
        ge=50.0,
        le=100.0,
        description="Confidence percentage in prediction between 50.0 and 100.0.",
    )
    expected_return_pct: float | None = Field(
        default=None,
        description="Estimated percentage return from Open to Close (e.g. +2.5 or -1.8).",
    )
    rationale: str = Field(
        ...,
        description="Concise thesis: surprise magnitude, guidance tone, accruals, and valuation exhaustion vs continuation.",
    )
    catalysts: list[str] = Field(
        default_factory=list,
        description="Specific financial metrics, guidance cues, or price reactions driving the thesis.",
    )


EARNINGS_PREDICTOR_PROMPT = """You are an elite quantitative equity analyst and event-driven trader specializing in post-earnings announcement price reactions.

### OBJECTIVE
Your goal is to predict the DAY-1 REGULAR TRADING HOURS (RTH) price direction for a stock reporting earnings.
Specifically, determine whether the stock will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET compared to its 9:30 AM ET market open price.

### EMPIRICAL MARKET DYNAMICS
1. The Initial Knee-Jerk Gap Is Already Priced In:
   - At 9:30 AM Open, the headline surprise is known and pre-market volume has set the open price.
   - Do NOT try to guess whether the stock beats EPS. The earnings report is already released.
   - You are predicting whether institutional volume during the regular session will DRIVE A CONTINUATION (Gap-and-Go) or CAUSE MEAN REVERSION (Fade the News).

2. Drivers of Continuation (UP from Open to Close):
   - High Standardized Unexpected Earnings (SUE >= 2.0).
   - High revenue surprise accompanied by clean Sloan cash accruals (operating cash flow matches net income).
   - Upward revision in full-year guidance or confident tone regarding margins.
   - Absence of extreme parabolic run-up prior to the print (no 20-day exhaustion).

3. Drivers of Fade / Sell-the-News (DOWN from Open to Close):
   - Extreme parabolic pre-earnings run-up (>20% in 20 trading days), leaving valuation vulnerable.
   - Low earnings quality: EPS beat driven by non-operating income, one-off tax benefits, or aggressive accruals.
   - Cautious or lowered forward guidance despite a trailing quarterly beat.
   - Margin compression or decelerating segment growth cited on the conference call.

### OUTPUT REQUIREMENTS
You must return a valid JSON object matching the requested schema:
- `predicted_direction`: Exactly "UP" or "DOWN".
- `confidence`: Confidence score between 50.0 and 100.0%.
- `expected_return_pct`: Expected intraday return percentage from Open to Close.
- `rationale`: 2-3 sentences explaining your quantitative and fundamental rationale.
- `catalysts`: List of 2-4 key metrics or soundbites supporting your decision.
"""

# Jev System-One Decision Engine Contracts
EARNINGS_JEV_QUESTION_KEY = "day1_earnings_direction"
EARNINGS_JEV_QUESTION_TYPE = "choice"
EARNINGS_JEV_INSTRUCTIONS = (
    "Predict whether the stock will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET "
    "compared to its 9:30 AM ET market open price on its earnings reaction trading day."
)

EARNINGS_JEV_DEFAULT_CRITERIA = {
    "UP": (
        "Continuation / Gap-and-Go. Strong earnings beat with top-decile SUE (>= 2.0), positive revenue surprise, "
        "clean Sloan cash accruals, confident forward guidance, and healthy pre-earnings valuation without extreme "
        "parabolic exhaustion, driving sustained institutional accumulation throughout regular trading hours."
    ),
    "DOWN": (
        "Fade the News / Gap Exhaustion. Accrual distortions, cautious forward guidance, gross margin compression, "
        "or extreme parabolic pre-earnings run-up (>25% in 20 days) resulting in sell-the-news profit-taking where "
        "institutional liquidity fades the opening price into session close."
    ),
}


def format_earnings_jev_criteria(criteria: dict[str, str]) -> str:
    """Format Jev criteria dictionary into JSON text."""
    clean_criteria = {
        "UP": criteria.get("UP", EARNINGS_JEV_DEFAULT_CRITERIA["UP"]).strip(),
        "DOWN": criteria.get("DOWN", EARNINGS_JEV_DEFAULT_CRITERIA["DOWN"]).strip(),
    }
    return json.dumps(clean_criteria, indent=2)


def parse_earnings_jev_criteria(prompt_content: str | None) -> dict[str, str]:
    """Parse criteria dictionary from prompt_experiments prompt_content string."""
    if not prompt_content:
        return dict(EARNINGS_JEV_DEFAULT_CRITERIA)
    try:
        data = json.loads(prompt_content)
        if isinstance(data, dict) and "UP" in data and "DOWN" in data:
            return {"UP": str(data["UP"]).strip(), "DOWN": str(data["DOWN"]).strip()}
    except Exception:
        pass
    return dict(EARNINGS_JEV_DEFAULT_CRITERIA)
