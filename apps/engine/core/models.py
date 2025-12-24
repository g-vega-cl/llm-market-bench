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

    @field_validator("ticker")
    @classmethod
    def upper_case_ticker(cls, v: str) -> str:
        """Normalize ticker symbols to uppercase."""
        return v.upper()
