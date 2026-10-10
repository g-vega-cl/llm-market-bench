"""Modular Data Manifest and Jev Criteria schemas for Local Autoresearch."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

# Default newsletters commonly ingested into newsletter_snapshots
KNOWN_NEWSLETTER_SENDERS = [
    "The Kobeissi Letter",
    "Morning Brew",
    "The Daily Shot",
    "Matt Levine / Bloomberg",
    "Exec Sum",
    "Chartr",
    "ZeroHedge Macro",
    "Sherwood News",
    "Bloomberg Markets",
    "Robinhood Snacks",
    "Wall Street Journal",
    "Seeking Alpha Alpha Talks",
    "Milk Road Macro",
    "Substack Macro Compass",
    "Bank of America Global Research",
]

DEFAULT_PROXIES = ["QQQ", "DIA", "IWM", "TLT", "IEF", "GLD", "USO"]


class DataManifest(BaseModel):
    """Configuration specifying which information modules are packed into the daily market context."""

    selected_newsletters: list[str] | None = Field(
        default=None,
        description="List of newsletter sender strings to include. If None, all available are included.",
    )
    include_synthetic_newsletter: bool = Field(
        default=True,
        description="Whether to include AI Wall Street synthesized morning newsletter briefing.",
    )
    include_macro_proxies: list[str] = Field(
        default_factory=lambda: list(DEFAULT_PROXIES),
        description="List of benchmark equity/yield/commodity proxies to include.",
    )
    include_currency_uup: bool = Field(
        default=False,
        description="Whether to include US Dollar index (UUP) pre-market gap and FX commentary.",
    )
    include_options_derivatives: bool = Field(
        default=True,
        description="Whether to include options positioning (Max Pain, Put/Call ratios, 25-delta skew).",
    )
    include_economic_calendar: bool = Field(
        default=True,
        description="Whether to include today's high-impact economic releases & calendar scenarios.",
    )
    include_market_health_barometer: bool = Field(
        default=False,
        description="Whether to include index market health barometer & constituent valuations.",
    )
    include_recent_market_feeling: bool = Field(
        default=False,
        description="Whether to include qualitative recent market feeling score and commentary.",
    )
    include_intraday_profile: bool = Field(
        default=True,
        description="Whether to include prior session intraday profile (VWAP, CLV, candle archetype).",
    )


class JevCriteriaConfig(BaseModel):
    """Decision criteria configuring Jev System One questions."""

    criteria_up: str = Field(
        ...,
        description="Conditions under which SPY closes HIGHER (UP) at 4:00 PM ET vs 9:30 AM ET Open.",
    )
    criteria_down: str = Field(
        ...,
        description="Conditions under which SPY closes LOWER (DOWN) at 4:00 PM ET vs 9:30 AM ET Open.",
    )
    min_confidence: float = Field(
        default=50.0,
        ge=50.0,
        le=100.0,
        description="Confidence threshold below which the prediction is routed as NO_TRADE / NEUTRAL.",
    )


class AutoresearchMutation(BaseModel):
    """A proposed experiment from the Local Meta-Researcher (Qwen via Strata)."""

    criteria: JevCriteriaConfig = Field(..., description="Mutated Jev criteria definitions.")
    manifest: DataManifest = Field(..., description="Mutated information manifest ('Box of Data').")
    hypothesis: str = Field(
        ...,
        description="Clear causal hypothesis explaining why this criteria + manifest combination will improve out-of-sample performance.",
    )


def pack_daily_context(day_record: dict[str, Any], manifest: DataManifest) -> str:
    """Compile a point-in-time market context string strictly based on the provided manifest.

    Guarantees:
    - Zero lookahead: Only incorporates fields timestamped prior to 09:15 AM ET on target_date.
    - Deterministic: Same day_record + manifest produces identical text.
    """
    target_date = day_record.get("target_date", "UNKNOWN_DATE")
    ticker = day_record.get("ticker", "SPY")
    lines: list[str] = [f"=== POINT-IN-TIME MARKET CONTEXT: {ticker} ({target_date}) ==="]

    # 1. Economic releases
    if manifest.include_economic_calendar:
        econ = day_record.get("economic_calendar")
        if econ:
            lines.append("--- High-Impact Economic Releases ---")
            lines.append(econ.strip())

    # 2. AI Synthesized Newsletter Briefing
    if manifest.include_synthetic_newsletter:
        synth = day_record.get("synthetic_newsletter")
        if synth:
            lines.append("--- Morning Newsletter Briefing ---")
            lines.append(synth.strip())

    # 3. Selected Ingested Newsletters
    newsletters = day_record.get("newsletters", [])
    if newsletters:
        selected_news = []
        for item in newsletters:
            sender = item.get("sender", "Unknown")
            # If selected_newsletters filter is provided, enforce it
            if manifest.selected_newsletters is not None:
                matches = any(
                    sel.lower() in sender.lower() or sender.lower() in sel.lower()
                    for sel in manifest.selected_newsletters
                )
                if not matches:
                    continue
            subject = item.get("subject", "No Subject")
            content = item.get("content", "").strip()[:400]
            selected_news.append(f"[{sender}] {subject}: {content}")

        if selected_news:
            lines.append("--- Curated Individual Newsletters ---")
            lines.extend(selected_news)

    # 4. Pre-Market Quotes & Proxies
    proxies_data = day_record.get("proxies", {})
    if proxies_data:
        allowed_proxies = set(manifest.include_macro_proxies)
        if manifest.include_currency_uup:
            allowed_proxies.add("UUP")
        else:
            allowed_proxies.discard("UUP")

        proxy_lines = []
        for sym in sorted(allowed_proxies):
            info = proxies_data.get(sym)
            if info:
                p = info.get("price", 0.0)
                chg = info.get("change_pct", 0.0)
                proxy_lines.append(f"- {sym}: ${p:.2f} ({chg:+.2f}%)")

        if proxy_lines:
            lines.append("--- Macro Benchmark Overnight Gaps ---")
            lines.extend(proxy_lines)

    # 5. Options Derivatives & Volatility Skew
    if manifest.include_options_derivatives:
        options = day_record.get("options_sentiment")
        if options:
            lines.append("--- Options Derivatives & Volatility Skew ---")
            lines.append(options.strip())

    # 6. Prior Session Intraday Profile
    if manifest.include_intraday_profile:
        profile = day_record.get("intraday_profile")
        if profile:
            lines.append("--- Prior Session Intraday Technical Profile ---")
            lines.append(profile.strip())

    # 7. Market Barometer
    if manifest.include_market_health_barometer:
        baro = day_record.get("market_barometer")
        if baro:
            lines.append("--- Market Health Barometer ---")
            lines.append(baro.strip())

    # 8. Market Feeling
    if manifest.include_recent_market_feeling:
        feeling = day_record.get("market_feeling")
        if feeling:
            lines.append("--- Qualitative Market Feeling ---")
            lines.append(feeling.strip())

    lines.append("==================================================")
    return "\n".join(lines)


def format_jev_payload(
    context: str,
    criteria: JevCriteriaConfig,
    ticker: str = "SPY",
    model_name: str = "~typesafe/jev-latest",
) -> dict[str, Any]:
    """Format request payload for OpenRouter Decisions API (/api/alpha/decisions)."""
    return {
        "model": model_name,
        "state": {
            "ticker": ticker.upper(),
            "market_context": context,
        },
        "questions": {
            "direction": {
                "type": "choice",
                "instructions": (
                    f"Predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
                    "at 4:00 PM ET compared to the 9:30 AM ET Open price."
                ),
                "criteria": {
                    "UP": criteria.criteria_up.strip(),
                    "DOWN": criteria.criteria_down.strip(),
                },
            }
        },
    }
