from typing import Literal
from pydantic import BaseModel, Field, field_validator

class DecisionObject(BaseModel):
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence: int = Field(..., ge=0, le=100, description="Confidence score between 0 and 100")
    reasoning: str = Field(..., description="Explanation of the decision based on the text")
    ticker: str = Field(..., description="Stock ticker symbol")
    source_id: str = Field(..., description="ID of the source newsletter chunk")

    @field_validator('ticker')
    @classmethod
    def upper_case_ticker(cls, v: str) -> str:
        return v.upper()
