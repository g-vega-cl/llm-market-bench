"""LLM logic for event synthesis and relationship analysis."""

import logging
import re
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from core import config
from core.llm import clients
from core.llm.logger import log_reasoning_trace
from core.llm.prompt_factory import PromptFactory

logger = logging.getLogger("engine")


def _normalize_future_date(date_str: str | None, note_str: str | None) -> tuple[str | None, str | None]:
    """Validates and normalizes the future date string.

    Returns:
        A tuple of (normalized_date, normalized_note).
    """
    if not date_str:
        return None, note_str

    # Strict ISO 8601 (YYYY-MM-DD) check
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date_str.strip()):
        try:
            # Validate actual date (e.g., no Feb 30)
            datetime.strptime(date_str.strip(), "%Y-%m-%d")
            return date_str.strip(), note_str
        except ValueError:
            pass

    # If it's not a valid ISO date, move it to the note if note is empty
    # or append it if note exists.
    if not note_str:
        return None, date_str.strip()

    if date_str.strip() not in note_str:
        return None, f"{note_str} ({date_str.strip()})"

    return None, note_str


async def synthesize_event(
    event_name: str, impact: str, reasonings: list[str], scenarios: list[str] = None
) -> dict[str, Any]:
    """Synthesizes a unified event name, summary, and stress-tested scenarios via a 2-stage debate.

    Stage 1: Adversarial Red-Team Challenger (gpt-5.6-luna) identifies counter-theses and failure modes.
    Stage 2: Arbiter / Synthesizer (gpt-5.6-luna) crafts balanced scenarios and hedged trading plans.

    Args:
        event_name: The raw representative event name.
        impact: The majority impact (BULLISH/BEARISH/NEUTRAL).
        reasonings: A list of reasoning strings from different models.
        scenarios: A list of initial scenario strings from different models.

    Returns:
        A dictionary with 'name', 'summary', 'scenarios', 'importance_score', and 'debate' keys.
    """
    import asyncio

    client = clients.get_openai_client()

    try:
        combined_reasonings = "\n".join([f"- {r}" for r in reasonings])
        combined_scenarios = (
            "\n".join([f"- {s}" for s in scenarios]) if scenarios else "No explicit scenario analysis provided."
        )

        # --- Stage 1: Adversarial Red-Team Challenger ---
        class ChallengerResponse(BaseModel):
            counter_thesis: str = Field(..., description="Main counter-thesis and alternative interpretation")
            pre_mortem_failure_mode: str = Field(
                ..., description="Why this trade/event could fail or reverse over 1-4 weeks"
            )
            key_risks: list[str] = Field(
                default_factory=list, description="Key unaddressed structural risks or headwinds"
            )

        challenger_messages = PromptFactory.build_challenger_messages(
            provider="openai",
            event_name=event_name,
            impact=impact,
            combined_reasonings=combined_reasonings,
            combined_scenarios=combined_scenarios,
        )

        challenger_awaitable = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            response_model=ChallengerResponse,
            messages=challenger_messages,
            reasoning_effort="none",
            max_retries=2,
        )

        if hasattr(challenger_awaitable, "__await__") or asyncio.iscoroutine(challenger_awaitable):
            challenger_resp = await challenger_awaitable
        else:
            challenger_resp = challenger_awaitable

        if not challenger_resp:
            challenger_resp = ChallengerResponse(
                counter_thesis="No explicit counter-thesis generated.",
                pre_mortem_failure_mode="General market regime shift or liquidity shock.",
                key_risks=[],
            )

        await log_reasoning_trace(
            task_type="CONSENSUS_CHALLENGE",
            model_provider="openai",
            model_name=config.OPENAI_MODEL,
            prompt=challenger_messages,
            response=challenger_resp,
            metadata={
                "event_name": event_name,
                "impact": impact,
            },
        )

        challenger_critique_text = (
            f"Counter-Thesis: {challenger_resp.counter_thesis}\n"
            f"Pre-Mortem Failure Mode: {challenger_resp.pre_mortem_failure_mode}\n"
            f"Key Unaddressed Risks: {', '.join(challenger_resp.key_risks) if challenger_resp.key_risks else 'None highlighted'}"
        )

        # --- Stage 2: Arbiter & Scenario Synthesizer ---
        class ScenarioDetail(BaseModel):
            cleanHeader: str = Field(..., description="The title of the scenario, e.g. 'Scenario A: Cut'")
            percentage: str | None = Field(None, description="Estimated probability percentage, e.g. '70%'")
            outcome: str = Field(..., description="Macroeconomic/market outcome description")
            tradingPlan: str | None = Field(None, description="Trading plan explaining how to profit")

        class SynthesisResponse(BaseModel):
            name: str
            summary: str
            future_date: str | None = None
            future_date_note: str | None = None
            is_ongoing: bool = False
            is_future_catalyst: bool = False
            historical_parallel: str | None = None
            scenarios: list[ScenarioDetail] = Field(
                default_factory=list,
                description="List of distinct possible scenarios. REQUIRED: At least two scenarios.",
            )
            importance_score: int = 5

        synthesis_messages = PromptFactory.build_synthesis_messages(
            provider="openai",
            event_name=event_name,
            impact=impact,
            combined_reasonings=combined_reasonings,
            combined_scenarios=combined_scenarios,
            challenger_critique=challenger_critique_text,
        )

        synthesis_awaitable = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            response_model=SynthesisResponse,
            messages=synthesis_messages,
            reasoning_effort="none",
            max_retries=2,
        )

        if hasattr(synthesis_awaitable, "__await__") or asyncio.iscoroutine(synthesis_awaitable):
            resp = await synthesis_awaitable
        else:
            resp = synthesis_awaitable

        if not resp:
            resp = SynthesisResponse(name=event_name, summary="Synthesis failed")

        # Post-process for date validity
        normalized_date, normalized_note = _normalize_future_date(resp.future_date, resp.future_date_note)

        # Log completion
        await log_reasoning_trace(
            task_type="CONSENSUS_SYNTHESIS",
            model_provider="openai",
            model_name=config.OPENAI_MODEL,
            prompt=synthesis_messages,
            response=resp,
            metadata={
                "event_name": event_name,
                "impact": impact,
                "normalized_date": normalized_date,
                "normalized_note": normalized_note,
            },
        )

        # Generate legacy scenario_analysis fallback string
        fallback_str = None
        if resp.scenarios:
            parts = []
            for s in resp.scenarios:
                pct = f" ({s.percentage} probability)" if s.percentage else ""
                parts.append(f"{s.cleanHeader}{pct}: {s.outcome} -> Trading Plan: {s.tradingPlan or 'None'}")
            fallback_str = " ".join(parts)

        debate_payload = {
            "challenger_critique": challenger_critique_text,
            "counter_thesis": challenger_resp.counter_thesis,
            "pre_mortem": challenger_resp.pre_mortem_failure_mode,
            "key_risks": challenger_resp.key_risks,
            "adversary_model": config.OPENAI_MODEL,
            "arbiter_model": config.OPENAI_MODEL,
            "stress_tested": True,
        }

        return {
            "name": resp.name,
            "summary": resp.summary,
            "future_date": normalized_date,
            "future_date_note": normalized_note,
            "is_ongoing": resp.is_ongoing,
            "is_future_catalyst": resp.is_future_catalyst,
            "historical_parallel": resp.historical_parallel,
            "scenarios": [s.model_dump() for s in resp.scenarios] if resp.scenarios else [],
            "scenario_analysis": fallback_str,
            "importance_score": resp.importance_score,
            "debate": debate_payload,
        }
    except Exception as e:
        logger.error("Event synthesis failed: %s", e)
        # Fallback to original if synthesis fails
        return {
            "name": event_name,
            "summary": (f"Consensus reached on {event_name} with {impact} impact based on model observations."),
            "future_date": None,
            "future_date_note": None,
            "is_ongoing": False,
            "is_future_catalyst": False,
            "historical_parallel": None,
            "scenarios": [],
            "scenario_analysis": None,
            "importance_score": 5,
            "debate": None,
        }
    finally:
        # Ensure client is properly closed
        await clients.close_client(client, "openai")


async def analyze_event_relationship(new_event: str, potential_ancestors: list[dict]) -> dict[str, Any]:
    """Analyzes the relationship between a new event and potential past events.

    Args:
        new_event: The summary of the new event.
        potential_ancestors: List of candidate past events from memory.

    Returns:
        A dictionary with 'parent_id', 'relationship_type', and 'should_resolve' (bool).
    """
    if not potential_ancestors:
        return {"parent_id": None, "relationship_type": None, "should_resolve": False}

    client = clients.get_openai_client()

    try:
        ancestors_text = ""
        for i, acc in enumerate(potential_ancestors):
            ancestors_text += f"\n[{i}] ID: {acc['id']}\nContent: {acc['content']}\n"

        messages = PromptFactory.build_relationship_messages(
            provider="openai",
            new_event=new_event,
            ancestors_text=ancestors_text,
        )

        class RelationshipResponse(BaseModel):
            parent_index: int | None = None
            relationship_type: str | None = None
            should_resolve: bool = False

        resp = await client.chat.completions.create(
            model=config.OPENAI_MODEL,
            response_model=RelationshipResponse,
            messages=messages,
            reasoning_effort="none",
            max_retries=2,
        )

        # Log completion
        await log_reasoning_trace(
            task_type="CONSENSUS_RELATIONSHIP",
            model_provider="openai",  # Hardcoded since analyze_event_relationship uses openai client
            model_name=config.OPENAI_MODEL,
            prompt=messages,
            response=resp,
            metadata={"new_event_preview": new_event[:100]},
        )

        result = {
            "parent_id": None,
            "relationship_type": resp.relationship_type,
            "should_resolve": resp.should_resolve,
        }
        if resp.parent_index is not None and 0 <= resp.parent_index < len(potential_ancestors):
            result["parent_id"] = potential_ancestors[resp.parent_index]["id"]

        return result
    except Exception as e:
        logger.error("Event relationship analysis failed: %s", e)
        return {"parent_id": None, "relationship_type": None, "should_resolve": False}
    finally:
        await clients.close_client(client, "openai")
