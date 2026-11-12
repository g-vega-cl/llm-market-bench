"""Schema definitions for Voxel Strategy Recipe DAGs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ConditionRule(BaseModel):
    """Single condition rule for technical or formula gates."""

    metric: str
    operator: Literal[">", "<", ">=", "<=", "=="]
    target: float | str


class NewsSourceConfig(BaseModel):
    bucket: str = "general_market"
    tickers: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    lookback_hours: int = 72


class TechnicalGateConfig(BaseModel):
    conditions: list[ConditionRule] = Field(default_factory=list)


class ClassificationConfig(BaseModel):
    model: str = "~typesafe/jev-latest"
    choices: list[str] = Field(default_factory=lambda: ["BULLISH", "BEARISH", "NEUTRAL"])
    target_choice: str = "BULLISH"
    min_confidence: float = 70.0


class GenerativeAnalystConfig(BaseModel):
    model: str = "auto-strata"
    system_prompt: str = "You are a quantitative market analyst."
    user_template: str = "Analyze catalyst: {{news.title}}\nTechnicals: {{tech.rsi_14}}"
    temperature: float = 0.0


class RiskOutputConfig(BaseModel):
    action: Literal["BUY", "SELL", "HOLD", "EXIT"] = "BUY"
    stop_loss_pct: float = 1.5
    target_profit_pct: float = 3.0
    max_hold_bars: int = 12
    exit_on_session_close: bool = True


class DAGNode(BaseModel):
    id: str
    type: Literal["news_source", "price_tape", "technical_gate", "classification", "generative_analyst", "risk_output"]
    title: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


class DAGEdge(BaseModel):
    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")

    model_config = {"populate_by_name": True}


class RecipeGraph(BaseModel):
    version: str = "1.0"
    id: str | None = None
    name: str = "Untitled Recipe"
    description: str = ""
    cadence: Literal["5m", "1d"] = "5m"
    concurrency: dict[str, Any] = Field(
        default_factory=lambda: {"max_open_trades": 3, "max_equity_pct_per_trade": 33.3}
    )
    nodes: list[DAGNode] = Field(default_factory=list)
    edges: list[DAGEdge] = Field(default_factory=list)
