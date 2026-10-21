from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

DAILY_PREDICTOR_CONSTRAINTS_HEADER = """You are an elite quantitative macro trader analyzing intraday S&P 500 (SPY) price action.
Your goal is to predict whether today's 4:00 PM ET Close price will be higher (UP) or lower (DOWN) than today's 9:30 AM ET Open price.

=== AVAILABLE MARKET CONTEXT ===
You are provided with point-in-time pre-market intelligence, which may include:
1. AI Wall Street synthesized morning newsletter briefing (macro narrative, sector spotlight, market internals & flows, trade ideas & scenarios), prior session macro regime baseline, sentiment barometers, and market feeling.
2. Live pre-market quotes & overnight gaps across major indices (SPY, QQQ, DIA, IWM), international proxies (EWJ, VGK), bond yield proxies (TLT, IEF), and commodities/FX (GLD, USO, UUP), where available.
3. Options derivatives positioning & volatility skew (Put/Call volume and open interest ratios, 25-delta volatility skew, ATM implied volatility, Max Pain strike), where available.
4. Historical price action & intraday profile, where available.
Base your analysis strictly on the data fields actually present in the session context.

"""

DAILY_PREDICTOR_MUTABLE_STRATEGIES = """=== ZERO-MEAN BASE RATE & ANTI-BIAS MANDATE ===
Intraday Open-to-Close returns follow a zero-mean distribution with near ~50/50 UP vs DOWN probability.
You MUST evaluate UP (bullish) and DOWN (bearish) scenarios with identical weight, rigor, and hurdle standards.
Do NOT default to DOWN due to macro anxiety or headline risk: markets frequently rally on "bad news priced in", oversold technical bounces, short covering, and earnings resilience.
Do NOT default to UP due to long-term drift: morning rallies frequently fade into gap-fill reversals or institutional distribution.

=== ANALYTICAL STRATEGY INSTRUCTIONS ===
1. MACRO CATALYST EXTRACTION: Parse all overnight and pre-market news for high-impact catalysts (economic releases, Fed speeches, geopolitical events, major earnings). Evaluate the EXPECTATION GAP:
- Bullish reaction: Positive surprise OR bad news already priced in / worse feared, triggering relief buying.
- Bearish reaction: Negative surprise OR good news already fully priced, triggering "sell the news" profit-taking.
Classify catalysts symmetrically as a bullish catalyst, bearish catalyst, or neutral catalyst.

2. TECHNICAL & PRICE ACTION SIGNALS (WHEN PROVIDED): When technical levels (previous day high/low, VWAP, moving averages) are present in the context:
- Evaluate bullish hold scenarios: price establishing above prior close/VWAP with constructive momentum.
- Evaluate bearish rejection scenarios: price capped below prior close/VWAP with deteriorating momentum.
If specific technical indicators are not provided in the context, rely on cross-asset signals (bonds, dollar, commodities) and catalyst severity.

3. MOMENTUM VS GAP-FILL & REVERSAL SYMMETRY: Quantify overnight gaps:
- For positive overnight gaps: symmetrically evaluate continuation (breakout drive) vs exhaustion / mean-reversion fade DOWN.
- For negative overnight gaps: symmetrically evaluate continuation (panic dump) vs dip-buying / short-squeeze reversal UP.
- For small/flat gaps (<0.2%): evaluate technical breakout vs breakdown triggers with equal probability.

4. SYMMETRIC CONFIDENCE CALIBRATION:
Confidence must scale symmetrically from 50% to 100% based on independent signal convergence:
- High UP confidence (>=65%) requires: clear bullish catalyst / relief trigger + cross-asset confirmation (e.g. yields easing, dollar soft, or strong sector breadth) + technical hold.
- High DOWN confidence (>=65%) requires: clear bearish catalyst / shock trigger + cross-asset confirmation (e.g. yields surging, dollar spike, or broad sector liquidation) + technical rejection.
Assign low-to-moderate confidence (52-58%) when signals conflict, when pre-market moves are unconfirmed by volume, or ahead of major midday events. Never exceed 80% confidence without multi-variable confirmation across both macro and market breadth."""

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


_CONTEXT_MARKER = "=== AVAILABLE MARKET CONTEXT ==="
_FROZEN_IDENTITY_LINE_PREFIXES = (
    "You are an elite quantitative macro trader",
    "Your goal is to predict whether today's 4:00 PM ET Close",
)


def _context_block_end(text: str, marker_idx: int) -> int:
    """Return the index just past the context block that starts at ``marker_idx``.

    The block ends at the first blank line or the next ``===`` section heading,
    whichever comes first.
    """
    pos = text.find("\n", marker_idx)
    while pos != -1:
        line_end = text.find("\n", pos + 1)
        line = text[pos + 1 : line_end if line_end != -1 else len(text)]
        if not line.strip() or line.startswith("==="):
            return pos
        pos = line_end
    return len(text)


def split_daily_predictor_prompt(prompt_text: str) -> tuple[str, str, str]:
    """Split DAILY_PREDICTOR_PROMPT into Header, Mutable Strategies, and Footer.

    Only the trader identity, the available market context description (header) and the
    JSON output format (footer) are frozen. Everything between them, including any
    base-rate / anti-bias guidance, is trading content owned by autoresearch. Legacy or
    duplicated structural constraints are cleanly stripped; a legacy stored prompt whose
    header contained the anti-bias mandate keeps it as mutable text.
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

    # 2. Strip frozen identity + market context (last occurrence eliminates duplicate headers)
    last_context_idx = content_before_footer.rfind(_CONTEXT_MARKER)
    if last_context_idx != -1:
        end_idx = _context_block_end(content_before_footer, last_context_idx)
        mutable = content_before_footer[end_idx:].strip()
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

    # 3. Defensive sanity check: remove any leftover frozen identity lines in mutable
    if any(prefix in mutable for prefix in _FROZEN_IDENTITY_LINE_PREFIXES):
        mutable = "\n".join(
            line for line in mutable.split("\n") if not line.startswith(_FROZEN_IDENTITY_LINE_PREFIXES)
        ).strip()

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
        if isinstance(data, dict):
            crit = data.get("criteria") if "criteria" in data and isinstance(data["criteria"], dict) else data
            if "UP" in crit and "DOWN" in crit:
                return {"UP": str(crit["UP"]).strip(), "DOWN": str(crit["DOWN"]).strip()}
    except Exception:
        pass

    return dict(JEV_DEFAULT_CRITERIA)


def parse_jev_curated_prompt_content(
    prompt_content: str | None,
) -> tuple[dict[str, str], float, dict[str, Any]]:
    """Parse criteria dictionary, min_confidence threshold, and manifest dictionary."""
    import json

    default_crit = dict(JEV_DEFAULT_CRITERIA)
    default_conf = 50.0
    default_manifest: dict[str, Any] = {}

    if not prompt_content:
        return default_crit, default_conf, default_manifest

    try:
        data = json.loads(prompt_content)
        if isinstance(data, dict):
            crit = data.get("criteria") if "criteria" in data and isinstance(data["criteria"], dict) else data
            up = str(crit.get("UP", default_crit["UP"])).strip()
            down = str(crit.get("DOWN", default_crit["DOWN"])).strip()
            min_conf = float(data.get("min_confidence", default_conf))
            manifest = data.get("manifest", {}) if isinstance(data.get("manifest"), dict) else {}
            return {"UP": up, "DOWN": down}, min_conf, manifest
    except Exception:
        pass

    return default_crit, default_conf, default_manifest


def format_jev_curated_prompt_content(
    criteria: dict[str, str],
    min_confidence: float = 50.0,
    manifest: dict[str, Any] | None = None,
) -> str:
    """Format Jev criteria, min_confidence, and data manifest as JSON for prompt_experiments."""
    import json

    payload = {
        "criteria": {
            "UP": criteria.get("UP", JEV_DEFAULT_CRITERIA["UP"]).strip(),
            "DOWN": criteria.get("DOWN", JEV_DEFAULT_CRITERIA["DOWN"]).strip(),
        },
        "min_confidence": round(float(min_confidence), 1),
        "manifest": manifest or {},
    }
    return json.dumps(payload, indent=2)


def parse_laya_curated_prompt_content(
    prompt_content: str | None,
) -> tuple[str, dict[str, str], float]:
    """Parse ingestion_prompt, criteria dictionary, and min_confidence threshold for Laya."""
    import json

    default_crit = dict(JEV_DEFAULT_CRITERIA)
    default_conf = 54.0
    default_ingestion = "Please synthesize pre-market observations into a structured briefing."

    if not prompt_content:
        return default_ingestion, default_crit, default_conf

    try:
        data = json.loads(prompt_content)
        if isinstance(data, dict):
            ingestion = str(data.get("ingestion_prompt", default_ingestion)).strip()
            crit = data.get("criteria") if "criteria" in data and isinstance(data["criteria"], dict) else data
            up = str(crit.get("UP", default_crit["UP"])).strip()
            down = str(crit.get("DOWN", default_crit["DOWN"])).strip()
            min_conf = float(data.get("min_confidence", default_conf))
            return ingestion, {"UP": up, "DOWN": down}, min_conf
    except Exception:
        pass

    return default_ingestion, default_crit, default_conf


def format_laya_curated_prompt_content(
    ingestion_prompt: str,
    criteria: dict[str, str],
    min_confidence: float = 54.0,
) -> str:
    """Format Laya double-ratchet ingestion prompt, criteria, and min_confidence as JSON for prompt_experiments."""
    import json

    payload = {
        "ingestion_prompt": ingestion_prompt.strip(),
        "criteria": {
            "UP": criteria.get("UP", JEV_DEFAULT_CRITERIA["UP"]).strip(),
            "DOWN": criteria.get("DOWN", JEV_DEFAULT_CRITERIA["DOWN"]).strip(),
        },
        "min_confidence": round(float(min_confidence), 1),
    }
    return json.dumps(payload, indent=2)
