"""Pydantic data models for structured LLM output.

This module defines the data models used for validating and structuring
LLM responses, ensuring type safety throughout the pipeline.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class DecisionObject(BaseModel):
    """Represents a trading decision from LLM analysis.

    This model captures the structured output from an LLM analyzing
    financial news, including the trading signal, confidence level,
    reasoning, and source attribution.

    Attributes:
        signal: The trading action (BUY, SELL, or HOLD).
        confidence: Confidence score between 0 and 100.
        reasoning: Explanation of the decision based on the analyzed text.
        ticker: Stock ticker symbol (automatically uppercased).
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
        confidence: Confidence score between 0 and 100.
        reasoning: Explanation for why this is a significant event.
        source_id: ID of the source newsletter chunk for attribution.
    """

    event_name: str = Field(..., description="Short name for the event")
    impact: Literal["BULLISH", "BEARISH", "NEUTRAL"]
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
