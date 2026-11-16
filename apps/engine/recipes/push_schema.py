"""Pydantic schemas for the 5-block push-based Strategy Builder MVP."""

from __future__ import annotations

import json
import re
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
    cadence: Literal["5m", "3h", "1d"] = "3h"
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


_TRADE_LINE_RE = re.compile(r"(?<!not\s)\b(BUY|SELL|EXIT)\s+([A-Z]{1,5})\b")
_VALID_ACTIONS = {"BUY", "SELL", "EXIT"}


def _parse_json_signal_array(chunk: str) -> list[dict[str, str]]:
    """Parse one candidate JSON array into validated BUY/SELL/EXIT signal dicts."""
    try:
        parsed = json.loads(chunk)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    signals: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "").upper().strip()
        ticker = str(item.get("ticker") or "").upper().strip()
        if action in _VALID_ACTIONS and ticker:
            signals.append({"action": action, "ticker": ticker})
    return signals


def parse_trade_signals(output_text: str) -> list[dict[str, str]]:
    """Extract BUY/SELL/EXIT ticker signals from JSON blocks or plain text."""
    if not output_text:
        return []

    for json_match in re.finditer(r"\[[\s\S]*?\]", output_text):
        signals = _parse_json_signal_array(json_match.group(0))
        if signals:
            return signals

    seen: set[tuple[str, str]] = set()
    signals: list[dict[str, str]] = []
    for action, ticker in _TRADE_LINE_RE.findall(output_text):
        key = (action, ticker)
        if key not in seen:
            seen.add(key)
            signals.append({"action": action, "ticker": ticker})
    return signals
