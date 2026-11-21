"""Pydantic schemas for the 5-block push-based Strategy Builder MVP."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


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
    blocks: list[StrategyBlock] = Field(default_factory=list)
    selected_tools: list[str] = Field(default_factory=list)


_RECIPE_NAMING_PATH = Path(__file__).resolve().parents[3] / "packages" / "config" / "recipe-naming.json"


@lru_cache(maxsize=1)
def recipe_naming() -> dict[str, Any]:
    """Shared web/engine naming contract (packages/config/recipe-naming.json)."""
    try:
        with open(_RECIPE_NAMING_PATH, encoding="utf-8") as fh:
            naming = json.load(fh)
        return {
            "defaultName": str(naming["defaultName"]),
            "nameMaxLength": int(naming["nameMaxLength"]),
        }
    except (OSError, KeyError, ValueError) as exc:
        raise RuntimeError(f"Recipe naming contract is missing or invalid: {_RECIPE_NAMING_PATH}") from exc


DEFAULT_STRATEGY_NAME: str = recipe_naming()["defaultName"]
RECIPE_NAME_MAX_LENGTH: int = recipe_naming()["nameMaxLength"]


class PushStrategy(BaseModel):
    """Top-level 5-block push-based strategy stored in strategy_recipes.graph_json.

    A strategy makes exactly one LLM call. The rule lives here so the engine can
    never run a recipe that chains a second call, and so the scheduler can skip
    a malformed recipe instead of queueing a job the worker would reject.
    """

    version: Literal["2.0-push"] = "2.0-push"
    id: str | None = None
    name: str = Field(default=DEFAULT_STRATEGY_NAME, max_length=RECIPE_NAME_MAX_LENGTH)
    description: str = ""
    cadence: Literal["5m", "3h", "1d"] = "3h"
    stages: list[StrategyStage] = Field(min_length=1, max_length=1)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: Any) -> str:
        """`strategy_recipes.name` is NOT NULL, so blank or null falls back.

        `graph_json` is free-form JSON: an older writer could store `name: null`,
        which must normalize instead of failing validation in the worker.
        """
        if not isinstance(value, str):
            return DEFAULT_STRATEGY_NAME
        return value.strip()[:RECIPE_NAME_MAX_LENGTH] or DEFAULT_STRATEGY_NAME

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

    @model_validator(mode="after")
    def enforce_block_contract(self) -> PushStrategy:  # noqa: F821 - postponed annotation
        """One block contract, enforced where every writer meets it.

        Block order is presentation, not an invariant: ``push_hydrator`` renders
        ``output_format`` last whatever the stored order, so the graph is
        normalised instead of rejected. Duplicate ids and a missing terminal block
        are hard errors — a graph without ``output_format`` makes the model reply
        in prose the signal parser drops, once per slot, silently.
        """
        stage = self.stages[0]
        ids = [block.id for block in stage.blocks]
        if len(set(ids)) != len(ids):
            raise ValueError("block ids must be unique")
        if not stage.blocks:
            # A placeholder graph with no blocks is pre-existing legacy data: it
            # renders nothing, but rejecting it would deactivate live recipes at
            # deploy time. Presence is enforced at the writer (compiler/studio).
            return self
        terminals = [block for block in stage.blocks if isinstance(block, OutputFormatBlock)]
        if len(terminals) != 1:
            raise ValueError("exactly one output_format block is required")
        stage.blocks = [
            block for block in stage.blocks if not isinstance(block, OutputFormatBlock)
        ] + terminals
        return self


_TRADE_LINE_RE = re.compile(r"(?<!not\s)\b(BUY|SELL|EXIT)\s+([A-Z]{1,5})\b")
_VALID_ACTIONS = {"BUY", "SELL", "EXIT"}


def is_valid_single_stage_graph(raw_graph: Any) -> bool:
    """True only when ``raw_graph`` validates as a single-stage Push v2 strategy.

    Shared by the scheduler (which skips invalid live recipes instead of queuing
    them) and the showcase publisher (which must not pin a graph the worker would
    reject). Accepts the stored JSON string form as well as a decoded dict.
    """
    if isinstance(raw_graph, str):
        try:
            raw_graph = json.loads(raw_graph)
        except json.JSONDecodeError:
            return False
    if not isinstance(raw_graph, dict):
        return False
    try:
        PushStrategy.model_validate(raw_graph)
    except ValidationError:
        return False
    return True


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
