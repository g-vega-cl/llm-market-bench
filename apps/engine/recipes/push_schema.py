"""Pydantic schemas for the 4-block push-based Strategy Builder MVP."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field


class PromptBlock(BaseModel):
    """Free-text prompt block injected directly into the stage prompt."""

    id: str
    type: Literal["prompt"] = "prompt"
    text: str = ""


class NewsBlock(BaseModel):
    """Point-in-time news filter block using keyword contains + recency."""

    id: str
    type: Literal["news"] = "news"
    contains: list[str] = Field(default_factory=list)
    recency_hours: int = 48


class MemoriesBlock(BaseModel):
    """Point-in-time memories filter block (contains, recency, category, min importance)."""

    id: str
    type: Literal["memories"] = "memories"
    contains: list[str] = Field(default_factory=list)
    recency_hours: int = 168
    category: str = "ALL"
    min_importance: int = Field(default=1, ge=1, le=10)


class TechnicalsRule(BaseModel):
    """Single technical or fundamental condition serialized as prompt instructions."""

    metric: str
    operator: Literal[">", "<", ">=", "<=", "=="] = ">"
    target: float | str = ""


class TechnicalsBlock(BaseModel):
    """Company technical/fundamental filter block serialized as prompt instructions for MVP."""

    id: str
    type: Literal["technicals"] = "technicals"
    rules: list[TechnicalsRule] = Field(default_factory=list)


StrategyBlock = Annotated[
    PromptBlock | NewsBlock | MemoriesBlock | TechnicalsBlock,
    Field(discriminator="type"),
]


class StrategyStage(BaseModel):
    """Single LLM execution stage with ordered push blocks and allowed tool names."""

    id: str
    title: str = "Stage 1"
    blocks: list[StrategyBlock] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)


class PushStrategy(BaseModel):
    """Top-level 4-block push-based strategy stored in strategy_recipes.graph_json."""

    version: Literal["2.0-push"] = "2.0-push"
    id: str | None = None
    name: str = "Untitled Strategy"
    description: str = ""
    cadence: Literal["5m", "1d"] = "1d"
    stages: list[StrategyStage] = Field(default_factory=list)
