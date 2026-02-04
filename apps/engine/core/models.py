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
    confidence: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score between 0 and 100"
    )
    reasoning: str = Field(
        ...,
        description="Explanation of the decision based on the text"
    )
    ticker: str = Field(..., description="Stock ticker symbol")
    catalyst_type: Literal["MACRO", "EARNINGS", "M_A", "PRODUCT", "REGULATORY", "OTHER"] = Field(
        "OTHER",
        description="The primary driver for this decision"
    )
    catalyst_duration: Literal["INTRADAY", "SHORT_TERM", "LONG_TERM"] = Field(
        "SHORT_TERM",
        description="The expected market impact timeframe"
    )
    source_id: str = Field(
        ...,
        description="ID of the source newsletter chunk"
    )
    model_provider: str | None = Field(
        None,
        description="LLM provider that generated the decision"
    )
    model_name: str | None = Field(
        None,
        description="Specific model name that generated the decision"
    )
    price: float | None = Field(
        None,
        description="The stock price mentioned or inferred from the news"
    )
    allocation_percentage: int | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentage of portfolio buying power to allocate to this trade (0-100)"
    )
    is_priced_in: bool = Field(
        False,
        description="Whether the news is already priced into the stock price"
    )
    is_priced_in_reasoning: str = Field(
        "No explicit priced-in reasoning provided.",
        description="Detailed reasoning for why this is or isn't priced in"
    )
    profit_potential_reasoning: str = Field(
        "No explicit profit potential reasoning provided.",
        description="Reasoning on why it's possible to make a profitable trade based on this"
    )

    @field_validator("ticker")
    @classmethod
    def upper_case_ticker(cls, v: str) -> str:
        """Normalize ticker symbols to uppercase."""
        return v.upper()


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
    catalyst_type: Literal["MACRO", "EARNINGS", "M_A", "PRODUCT", "REGULATORY", "OTHER"] = Field(
        "MACRO",
        description="The category of market event"
    )
    is_ongoing: bool | None = Field(
        False, 
        description="Whether the event is currently unfolding and unresolved (e.g. 'Trade War Escalating')"
    )
    is_future_catalyst: bool | None = Field(
        False,
        description="Whether this event is a precursor or 'armada' for a future market move"
    )
    historical_parallel: str | None = Field(
        None,
        description="A historical comparison mentioned (e.g. 'Like the 1970s stagflation')"
    )
    is_government_incentive: bool = Field(
        False,
        description="Whether this event is related to government budgets, objectives, or incentives"
    )
    expiry_date: str | None = Field(
        None,
        description="The date or timeframe when this incentive or policy expires (e.g., '2027')"
    )
    confidence: int = Field(..., ge=0, le=100)
    reasoning: str = Field(..., description="Explanation of the event's significance")
    source_id: str = Field(..., description="ID of the source newsletter chunk")
    model_provider: str | None = Field(None)
    model_name: str | None = Field(None)


class DecisionsResponse(BaseModel):
    """Container for trading decisions and macro events from a batch analysis."""
    decisions: list[DecisionObject] = Field(
        default_factory=list,
        description="List of trading decisions generated from the batch of news"
    )
    macro_events: list[MacroEvent] = Field(
        default_factory=list,
        description="List of broad market events or themes identified"
    )


class NewsletterCleaningResponse(BaseModel):
    """Represents the output of the newsletter de-advertisement pass.

    Attributes:
        cleaned_content: The newsletter body with advertisements removed.
        ads_removed_count: Number of advertisement blocks identified and removed.
    """

    cleaned_content: str = Field(..., description="The cleaned newsletter text")
    ads_removed_count: int = Field(0, description="Number of ad blocks removed")
