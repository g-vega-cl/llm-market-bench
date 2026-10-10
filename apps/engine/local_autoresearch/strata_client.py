"""Local Meta-Researcher client communicating with Qwen via Strata on localhost."""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any

import httpx

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.engine.local_autoresearch.manifest import (
    KNOWN_NEWSLETTER_SENDERS,
    AutoresearchMutation,
    DataManifest,
    JevCriteriaConfig,
)

DEFAULT_STRATA_URL = os.getenv("STRATA_BASE_URL", "http://localhost:8080/v1")
DEFAULT_STRATA_MODEL = os.getenv("STRATA_MODEL", "qwen3.8-flash-next-iq2_xs")

STRATA_META_RESEARCHER_SYSTEM = f"""You are an autonomous quantitative meta-researcher optimizing an intraday S&P 500 (SPY) prediction machine.
You control two critical levers:
1. THE DECISION CRITERIA for Jev (System One choice model):
   - `criteria_up`: 2-3 precise, testable pre-market conditions indicating SPY 4:00 PM Close >= 9:30 AM Open.
   - `criteria_down`: 2-3 symmetric pre-market conditions indicating SPY 4:00 PM Close < 9:30 AM Open.
   - `min_confidence`: Confidence threshold (50.0 to 80.0) below which the model refuses to trade (NO_TRADE).
2. THE INFORMATION MANIFEST ("Box of Data"):
   - `selected_newsletters`: Out of the available newsletters, choose which ones to include. Removing noisy, confusing, or low-quality newsletters is highly encouraged.
   - Available newsletters: {json.dumps(KNOWN_NEWSLETTER_SENDERS)}
   - `include_synthetic_newsletter`: (true/false) AI Wall Street synthesized morning briefing.
   - `include_macro_proxies`: List of symbols from ["QQQ", "DIA", "IWM", "TLT", "IEF", "GLD", "USO"].
   - `include_currency_uup`: (true/false) Pre-market US Dollar index move. Note: currency noise can confuse equity trend classification.
   - `include_options_derivatives`: (true/false) Put/Call ratios, Max Pain, and volatility skew.
   - `include_economic_calendar`: (true/false) Today's high-impact economic releases (8:30 AM prints vs consensus).
   - `include_market_health_barometer`: (true/false) Index breadth and valuation barometer.
   - `include_recent_market_feeling`: (true/false) Qualitative daily market feeling text.
   - `include_intraday_profile`: (true/false) Prior session completed VWAP, CLV, and candlestick archetype.

=== STRICT TEMPORAL PRE-MARKET CONSTRAINT (MANDATORY) ===
All predictions run strictly PRE-MARKET before the 9:30 AM ET opening bell (typically 09:15 AM ET).
You MUST NEVER reference post-open intraday data (such as 'first 30-minute return', 'first 15 minutes', 'first candle', or 'current-day VWAP').
Any criteria referencing current-day post-open data are unobservable at 09:15 AM ET and will be rejected.
All criteria must be testable using ONLY observable pre-market features:
1. Overnight index futures gaps (e.g. QQQ overnight gap vs SPY overnight gap).
2. Pre-market economic prints (e.g. 8:30 AM jobless claims, CPI surprise vs consensus).
3. Morning newsletter sentiment & institutional commentary.
4. Prior session technical profile (yesterday's close vs yesterday's VWAP, yesterday's candle archetype, yesterday's CLV).

=== CRITICAL PRINCIPLES ===
1. SYMMETRY & ZERO-MEAN: Avoid bullish bias. Close-to-open returns are roughly 50/50. Criteria must be balanced.
2. OVERFITTING PREVENTION: Do not write rules tuned to specific historical dates or single-day quirks. Generalize.
3. DATA PRUNING: Less is often more. If passing currencies or too many newsletters creates conflicting signals, prune them.
4. CAUSAL HYPOTHESIS: State clearly what changed and why you expect out-of-sample test accuracy to improve.
5. CONCISE REASONING: Keep internal chain-of-thought reasoning brief (under 150 words). Immediately produce the final JSON.

OUTPUT FORMAT:
You MUST respond with a single valid JSON object strictly matching this schema:
{{
  "criteria": {{
    "criteria_up": "...",
    "criteria_down": "...",
    "min_confidence": 55.0
  }},
  "manifest": {{
    "selected_newsletters": ["The Kobeissi Letter", "ZeroHedge Macro"],
    "include_synthetic_newsletter": true,
    "include_macro_proxies": ["QQQ", "TLT", "GLD"],
    "include_currency_uup": false,
    "include_options_derivatives": true,
    "include_economic_calendar": true,
    "include_market_health_barometer": false,
    "include_recent_market_feeling": false,
    "include_intraday_profile": true
  }},
  "hypothesis": "Concise causal reason for this mutation."
}}
"""


async def is_strata_available(base_url: str = DEFAULT_STRATA_URL) -> bool:
    """Check if the local Strata inference server is responding."""
    try:
        url = f"{base_url.rstrip('/')}/models"
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(url)
            return resp.status_code == 200
    except Exception:
        return False


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    """Robustly parse JSON object from raw LLM output."""
    clean = raw_text.strip()
    if clean.startswith("```"):
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean)
        if match:
            clean = match.group(1).strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        # Fallback regex search for outer JSON braces
        brace_match = re.search(r"(\{[\s\S]*\})", clean)
        if brace_match:
            return json.loads(brace_match.group(1))
        raise


async def generate_mutation_with_strata(
    baseline_criteria: JevCriteriaConfig,
    baseline_manifest: DataManifest,
    baseline_score: float,
    train_score: float,
    test_score: float,
    memories_context: str = "",
    recent_errors_summary: str = "",
    base_url: str = DEFAULT_STRATA_URL,
    model_name: str = DEFAULT_STRATA_MODEL,
    client: httpx.AsyncClient | None = None,
) -> AutoresearchMutation:
    """Ask local Qwen via Strata to synthesize the next experimental criteria and data manifest."""
    user_prompt = f"""### CURRENT ACTIVE BASELINE STATUS:
- Baseline Ratchet Score: {baseline_score:.2f}
- Recent Train Score: {train_score:.2f} | Test Score: {test_score:.2f}

### CURRENT DECISION CRITERIA:
- UP: {baseline_criteria.criteria_up}
- DOWN: {baseline_criteria.criteria_down}
- Min Confidence Gate: {baseline_criteria.min_confidence:.1f}%

### CURRENT DATA MANIFEST:
{json.dumps(baseline_manifest.model_dump(), indent=2)}

{memories_context}

{recent_errors_summary}

### TASK:
Generate a refined `criteria` and `manifest` mutation that improves out-of-sample Test Score while minimizing overfitting.
Prune confusing information channels or adjust technical thresholds.
Return ONLY valid JSON.
"""

    headers = {"Content-Type": "application/json"}
    reasoning_budget = int(os.getenv("STRATA_REASONING_BUDGET_TOKENS", "512"))
    max_tokens = int(os.getenv("STRATA_MAX_TOKENS", "2048"))
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": STRATA_META_RESEARCHER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,
        "reasoning_budget_tokens": reasoning_budget,
        "max_tokens": max_tokens,
    }

    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=180.0)
        should_close = True

    try:
        url = f"{base_url.rstrip('/')}/chat/completions"
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"Strata API returned HTTP {resp.status_code}: {resp.text}")

        resp_json = resp.json()
        raw_content = resp_json["choices"][0]["message"]["content"]
        data = _extract_json_payload(raw_content)

        return AutoresearchMutation.model_validate(data)
    finally:
        if should_close:
            await client.aclose()
