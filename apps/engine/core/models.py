"""Pydantic data models for structured LLM output.

This module defines the data models used for validating and structuring
LLM responses, ensuring type safety throughout the pipeline.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DecisionObject(BaseModel):
    """Represents a trading decision from LLM analysis.

    This model captures the structured output from an LLM analyzing
    financial news, including the trading signal, catalyst type,
    expected duration, and source attribution.

    Attributes:
        signal: The trading action (BUY, SELL, or HOLD).
        confidence: Confidence score between 0 and 100.
        reasoning: Explanation of the decision based on the analyzed text.
        ticker: Stock ticker symbol (automatically uppercased).
        catalyst_type: The primary driver of the trade (MACRO, EARNINGS, etc.).
        catalyst_duration: Expected timeframe for the catalyst (INTRADAY, etc.).
        source_id: ID of the source newsletter chunk for attribution.
    """

    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: int = Field(..., ge=0, le=100, description="Confidence score between 0 and 100")
    reasoning: str = Field(..., description="Explanation of the decision based on the text")
    ticker: str = Field(..., description="Stock ticker symbol")
    catalyst_type: Literal[
        "MACRO",
        "EARNINGS",
        "M_A",
        "PRODUCT",
        "REGULATORY",
        "EVENT",
        "INNOVATION",
        "TECHNICAL",
        "UNCROWDED_TRADE",
        "OTHER",
    ] = Field("OTHER", description="The primary driver for this decision")
    catalyst_duration: Literal["INTRADAY", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"] = Field(
        "SHORT_TERM", description="The expected market impact timeframe"
    )
    source_id: str = Field(..., description="ID of the source newsletter chunk")
    model_provider: str | None = Field(None, description="LLM provider that generated the decision")
    model_name: str | None = Field(None, description="Specific model name that generated the decision")
    allocation_percentage: int | None = Field(
        20, ge=0, le=100, description="Percentage of portfolio buying power to allocate to this trade (0-100)"
    )
    is_priced_in: bool = Field(False, description="Whether the news is already priced into the stock price")
    is_priced_in_reasoning: str = Field(
        "No explicit priced-in reasoning provided.", description="Detailed reasoning for why this is or isn't priced in"
    )
    profit_potential_reasoning: str = Field(
        "No explicit profit potential reasoning provided.",
        description="Reasoning on why it's possible to make a profitable trade based on this",
    )
    strategy_reasoning: str | None = Field(None, description="Detailed strategic reasoning for the trade")
    advance_planning_notes: str | None = Field(
        None, description="Notes for planning decisions in advance (e.g., selling X for Y)"
    )
    buy_tool_called: bool = Field(
        False, description="MANDATORY for BUY: Whether the buy quantity tool was called to verify position size"
    )
    sell_tool_called: bool = Field(
        False, description="MANDATORY for SELL: Whether the sell quantity tool was called to verify position size"
    )
    quantity: int | None = Field(
        None, ge=0, description="The exact quantity of shares to trade (mandatory if sell_tool_called is true)"
    )
    injected_market_price: float | None = Field(
        None, description="Market price injected into the prompt for this ticker (set by the system, not the LLM)"
    )
    original_index: int | None = Field(
        None, description="Stable sequence number preserving the model's original reasoning order"
    )

    @field_validator("ticker")
    @classmethod
    def upper_case_ticker(cls, v: str) -> str:
        """Normalize ticker symbols to uppercase."""
        return v.upper()

    @field_validator("signal", mode="before")
    @classmethod
    def normalize_signal(cls, v: str) -> str:
        """Normalize signal casing and whitespace."""
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper in {"BUY", "SELL", "HOLD"}:
                return v_upper
        return v

    @field_validator("catalyst_type", mode="before")
    @classmethod
    def normalize_catalyst_type(cls, v: str) -> str:
        """Gracefully handle custom or mismatched catalyst types by mapping or defaulting to OTHER."""
        if not isinstance(v, str):
            return v
        v_upper = v.upper().strip()
        allowed = {
            "MACRO",
            "EARNINGS",
            "M_A",
            "PRODUCT",
            "REGULATORY",
            "EVENT",
            "INNOVATION",
            "TECHNICAL",
            "UNCROWDED_TRADE",
            "OTHER",
        }
        if v_upper in allowed:
            return v_upper

        # Common variations mapping
        mapping = {
            "MERGERS": "M_A",
            "ACQUISITIONS": "M_A",
            "MERGER": "M_A",
            "ACQUISITION": "M_A",
            "M&A": "M_A",
            "MACRO_ECONOMICS": "MACRO",
            "MACROECONOMIC": "MACRO",
            "POLITICS": "MACRO",
            "GEOPOLITICS": "MACRO",
            "REGULATION": "REGULATORY",
            "LEGISLATION": "REGULATORY",
            "EARNING": "EARNINGS",
            "PRODUCT_LAUNCH": "PRODUCT",
        }
        return mapping.get(v_upper, "OTHER")

    @field_validator("catalyst_duration", mode="before")
    @classmethod
    def normalize_catalyst_duration(cls, v: str) -> str:
        """Gracefully handle duration formatting variations, falling back to SHORT_TERM."""
        if not isinstance(v, str):
            return v
        v_upper = v.upper().replace("-", "_").replace(" ", "_").strip()
        allowed = {"INTRADAY", "SHORT_TERM", "MEDIUM_TERM", "LONG_TERM"}
        if v_upper in allowed:
            return v_upper

        mapping = {
            "SHORT": "SHORT_TERM",
            "MEDIUM": "MEDIUM_TERM",
            "LONG": "LONG_TERM",
        }
        return mapping.get(v_upper, "SHORT_TERM")


class MacroEvent(BaseModel):
    """Represents a broad market theme or event identified by LLM analysis.

    Attributes:
        event_name: Short name for the event (e.g., "Fed Rate Hike").
        impact: Expected market impact (BULLISH, BEARISH, or NEUTRAL).
        catalyst_type: The category of market event.
        confidence: Confidence score between 0 and 100.
        reasoning: Explanation for why this is a significant event.
        source_id: ID of the source newsletter chunk for attribution.
    """

    event_name: str = Field(..., description="Short name for the event")
    impact: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    catalyst_type: Literal[
        "MACRO",
        "EARNINGS",
        "M_A",
        "PRODUCT",
        "REGULATORY",
        "EVENT",
        "INNOVATION",
        "TECHNICAL",
        "UNCROWDED_TRADE",
        "OTHER",
    ] = Field("MACRO", description="The category of market event")
    is_ongoing: bool | None = Field(
        False,
        description="Whether the event is a currently unfolding trend, rotation, or unresolved past action (e.g. 'Structural Rotation into HALO', 'Nvidia Photonics Investment')",
    )
    is_future_catalyst: bool | None = Field(
        False,
        description="Whether this is strictly a PENDING, UPCOMING event with multiple possible future outcomes (e.g. 'OPEC meeting', 'Elections', 'Data release'). Do NOT mark past investments or ongoing trends as future catalysts.",
    )
    historical_parallel: str | None = Field(
        None, description="A historical comparison mentioned (e.g. 'Like the 1970s stagflation')"
    )
    expiry_date: str | None = Field(
        None, description="The date or timeframe when this incentive or policy expires (e.g., '2027')"
    )
    target_date: str | None = Field(
        None, description="Event target date in YYYY-MM-DD format (or None)"
    )
    importance_score: int = Field(5, ge=1, le=10, description="Intrinsic importance of the event (1-10)")
    confidence: int = Field(..., ge=0, le=100)
    reasoning: str = Field(..., description="Explanation of the event's significance")
    scenario_analysis: str | None = Field(
        None,
        description="Analysis of potential resolutions. REQUIRED for Future Catalysts: Include at least two distinct outcomes (scenarios) AND a specific 'Trading Plan' for each (e.g., 'Scenario A: [Outcome] -> Trading Plan: [Action]').",
    )
    source_id: str = Field("unknown", description="ID of the source newsletter chunk")
    model_provider: str | None = Field(None)
    model_name: str | None = Field(None)

    @field_validator("impact", mode="before")
    @classmethod
    def normalize_impact(cls, v: str) -> str:
        """Normalize impact casing and whitespace."""
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper in {"BULLISH", "BEARISH", "NEUTRAL"}:
                return v_upper
        return v

    @field_validator("catalyst_type", mode="before")
    @classmethod
    def normalize_catalyst_type(cls, v: str) -> str:
        """Gracefully handle custom or mismatched catalyst types for MacroEvent, defaulting to MACRO."""
        if not isinstance(v, str):
            return v
        v_upper = v.upper().strip()
        allowed = {
            "MACRO",
            "EARNINGS",
            "M_A",
            "PRODUCT",
            "REGULATORY",
            "EVENT",
            "INNOVATION",
            "TECHNICAL",
            "UNCROWDED_TRADE",
            "OTHER",
        }
        if v_upper in allowed:
            return v_upper

        # Common variations mapping
        mapping = {
            "MERGERS": "M_A",
            "ACQUISITIONS": "M_A",
            "MERGER": "M_A",
            "ACQUISITION": "M_A",
            "M&A": "M_A",
            "MACRO_ECONOMICS": "MACRO",
            "MACROECONOMIC": "MACRO",
            "POLITICS": "MACRO",
            "GEOPOLITICS": "MACRO",
            "REGULATION": "REGULATORY",
            "LEGISLATION": "REGULATORY",
            "EARNING": "EARNINGS",
            "PRODUCT_LAUNCH": "PRODUCT",
        }
        return mapping.get(v_upper, "MACRO")


class DecisionsResponse(BaseModel):
    """Container for trading decisions and macro events from a batch analysis."""

    decisions: list[DecisionObject] = Field(
        default_factory=list, description="List of trading decisions generated from the batch of news"
    )
    macro_events: list[MacroEvent] = Field(
        default_factory=list, description="List of broad market events or themes identified"
    )

    @field_validator("decisions", "macro_events", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        """Handle cases where LLM returns a JSON string instead of a list."""
        if isinstance(v, str):
            try:
                import json

                return json.loads(v)
            except Exception:
                return v
        return v


class NewsletterCleaningResponse(BaseModel):
    """Represents the output of the newsletter de-advertisement pass.

    Attributes:
        cleaned_content: The newsletter body with advertisements removed.
        ads_removed_count: Number of advertisement blocks identified and removed.
    """

    cleaned_content: str = Field(..., description="The cleaned newsletter text")
    ads_removed_count: int = Field(0, description="Number of ad blocks removed")


class VerificationResult(BaseModel):
    """Represents the outcome of the 'second reasoning step' verification.

    Attributes:
        status: The verification result (APPROVED, REJECTED_VERIFICATION, or ADJUSTED_ALLOCATION).
        verification_reasoning: Detailed explanation of the second-step thinking.
        adjusted_quantity: If allocation is adjusted, the new share count.
        alternative_ticker: If a better play was found, the suggested ticker.
        confidence_score: Confidence in the verification (0-100).
    """

    status: Literal["APPROVED", "REJECTED_VERIFICATION", "ADJUSTED_ALLOCATION"]
    verification_reasoning: str = Field(..., description="Detailed explanation of the second-step thinking")
    adjusted_quantity: int | None = Field(None, description="New quantity if allocation is adjusted")
    alternative_ticker: str | None = Field(None, description="Suggested alternative stock ticker")
    confidence_score: int = Field(..., ge=0, le=100, description="Confidence score for this verification")

    @field_validator("status", mode="before")
    @classmethod
    def normalize_status(cls, v: str) -> str:
        """Normalize verification status casing and mapping."""
        if isinstance(v, str):
            v_upper = v.upper().strip()
            if v_upper in {"APPROVED", "REJECTED_VERIFICATION", "ADJUSTED_ALLOCATION"}:
                return v_upper
            if v_upper == "REJECTED":
                return "REJECTED_VERIFICATION"
        return v


class CauseAndEffectResult(BaseModel):
    """Represents the impact analysis of a market event.

    Attributes:
        analysis: Detailed breakdown of the cause and effect relationship.
        market_outcome: Concise summary of what actually happened.
        confidence: Confidence in the causal link (0-100).
        tags: List of relevant tags for classification.
    """

    analysis: str = Field(..., description="Detailed breakdown of the cause and effect relationship")
    market_outcome: str = Field(..., description="Concise summary of actual market movement")
    confidence: int = Field(..., ge=0, le=100, description="Confidence in the causal link")
    tags: list[str] = Field(default_factory=list, description="Relevant tags for classification")


class TickerSuggestion(BaseModel):
    """Represents a list of suggested tickers for a market event.

    Attributes:
        tickers: List of stock/ETF ticker symbols.
        reasoning: Brief explanation of why these tickers are relevant.
    """

    tickers: list[str] = Field(..., description="List of stock or ETF ticker symbols")
    reasoning: str = Field(..., description="Brief explanation of relevance")

    @field_validator("tickers")
    @classmethod
    def upper_case_tickers(cls, v: list[str]) -> list[str]:
        """Normalize all tickers to uppercase."""
        return [t.upper() for t in v]


class DiscoveryThemes(BaseModel):
    """Sectors, industries, and keywords for asset discovery."""

    sectors: list[str] = Field(default_factory=list, description="List of FMP-compatible sectors")
    industries: list[str] = Field(default_factory=list, description="List of FMP-compatible industries")
    keywords: list[str] = Field(default_factory=list, description="Keywords for ticker search")
    market_cap_min: float | None = Field(None, description="Minimum market cap in USD (optional)")
    reasoning: str = Field(..., description="Strategic reasoning for these discovery targets")


class RankedAsset(BaseModel):
    """A ticker that has been ranked for relevance to a specific event."""

    ticker: str = Field(..., description="Stock ticker symbol")
    name: str = Field(..., description="Company or ETF name")
    relevance_score: int = Field(..., ge=0, le=100, description="How well this asset matches the theme (0-100)")
    reason: str = Field(..., description="Specific reasoning for why this asset is a good play for this event")

    @field_validator("ticker")
    @classmethod
    def upper_case_ticker(cls, v: str) -> str:
        return v.upper()


class DiscoveryRankingResponse(BaseModel):
    """Container for the re-ranking step of discovery."""

    ranked_assets: list[RankedAsset] = Field(
        default_factory=list, description="List of assets ranked by thematic relevance"
    )


class MacroEventsResponse(BaseModel):
    """Container for macro events identified from batch analysis."""

    macro_events: list[MacroEvent] = Field(
        default_factory=list, description="List of broad market events or themes identified"
    )

    @field_validator("macro_events", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            try:
                import json

                return json.loads(v)
            except Exception:
                return v
        return v


class TradingDecisionsResponse(BaseModel):
    """Container for trading decisions generated from batch analysis."""

    decisions: list[DecisionObject] = Field(default_factory=list, description="List of trading decisions generated")

    @field_validator("decisions", mode="before")
    @classmethod
    def parse_json_string(cls, v):
        if isinstance(v, str):
            try:
                import json

                return json.loads(v)
            except Exception:
                return v
        return v
