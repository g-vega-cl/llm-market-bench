"""Pydantic schemas for the 5-block push-based Strategy Builder MVP."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class OutputFormatBlock(BaseModel):
    """Immutable output format contract locked to the trade-signal schema.

    Rendered verbatim as the final instruction block so model output matches
    [{"action": "BUY"|"SELL", "ticker": "..."}] exactly. Content is frozen;
    users may add or remove the block but not edit its rendered text.
    """

    id: str
    type: Literal["output_format"] = "output_format"

    model_config = ConfigDict(frozen=True)


StrategyBlock = Annotated[
    PromptBlock | NewsBlock | MemoriesBlock | TechnicalsBlock | OutputFormatBlock,
    Field(discriminator="type"),
]


class StrategyStage(BaseModel):
    """Single LLM execution stage with ordered push blocks and allowed tool names."""

    id: str
    title: str = "Stage 1"
    blocks: list[StrategyBlock] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)


class PushStrategy(BaseModel):
    """Top-level 5-block push-based strategy stored in strategy_recipes.graph_json.

    A strategy makes exactly one LLM call. The rule lives here so the engine can
    never run a recipe that chains a second call, and so the scheduler can skip
    a malformed recipe instead of queueing a job the worker would reject.
    """

    version: Literal["2.0-push"] = "2.0-push"
    id: str | None = None
    name: str = "Untitled Strategy"
    description: str = ""
    cadence: Literal["5m", "1d"] = "1d"
    stages: list[StrategyStage] = Field(min_length=1, max_length=1)

    @field_validator("stages", mode="before")
    @classmethod
    def validate_exactly_one_llm_stage(cls, stages: Any) -> Any:
        if isinstance(stages, list) and len(stages) != 1:
            raise ValueError("Push strategies must contain exactly one LLM stage for the MVP")
        return stages

    @field_validator("stages")
    @classmethod
    def reject_prev_output_placeholder(cls, stages: list[StrategyStage]) -> list[StrategyStage]:
        """A single-stage strategy has no previous output to reference.

        Left in place, the placeholder is substituted with an empty string and the
        model silently receives a truncated prompt, so it is rejected instead.
        """
        for stage in stages:
            for block in stage.blocks:
                if isinstance(block, PromptBlock) and "{{prev_output}}" in block.text:
                    raise ValueError("prev_output is not available in a single-stage strategy; remove the placeholder")
        return stages

    @field_validator("stages")
    @classmethod
    def validate_single_llm_stage(cls, stages: list[StrategyStage]) -> list[StrategyStage]:
        if len(stages) > 1:
            raise ValueError("Push strategies are limited to one LLM stage for the MVP")
        return stages
