"""Event Consensus Protocol logic.

This module implements the logic to compare macro events from multiple LLM models
and promote them to the global timeline (long-term memory) if consensus is reached.
"""

import logging
from collections import defaultdict
from typing import Any

import numpy as np

from analysis.discovery_service import DiscoveryService
from core.config import MODEL_WEIGHTS
from core.llm import analyze_event_relationship, synthesize_event
from core.models import DecisionObject, MacroEvent
from memory.embeddings import get_embeddings_batch
from memory.store import add_memory, find_potential_ancestors, update_memory_status

logger = logging.getLogger("engine")


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes the cosine similarity between two vectors."""
    if not v1 or not v2:
        return 0.0
    a = np.array(v1)
    b = np.array(v2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def _resolve_impact_tie(impact_weights: dict[str, float]) -> str:
    """Resolve impact when there's a tie using weighted votes, defaulting to NEUTRAL.

    Args:
        impact_weights: Dictionary mapping impact types to their weighted totals.

    Returns:
        The majority impact (weighted), or NEUTRAL if there's a tie.
    """
    if not impact_weights:
        return "NEUTRAL"

    max_weight = max(impact_weights.values())
    top_impacts = [k for k, v in impact_weights.items() if v == max_weight]

    # Clear winner
    if len(top_impacts) == 1:
        return top_impacts[0]

    # Weighted Tie: if NEUTRAL is one of the top, prefer it; otherwise default to NEUTRAL
    return "NEUTRAL"


_VAGUE_GOVERNMENT_PATTERNS = [
    "government policy update",
    "government policy structural",
    "legislative policy developments",
    "ongoing legislative policy",
    "ongoing policy",
    "policy update",
    "policy structural update",
    "regulatory update",
    "regulatory policy",
    "vague_government_event",
]


def _is_vague_government_event(name: str, summary: str = "") -> bool:
    """Checks whether a synthesized event is a vague government event lacking specific policy identifiers."""
    name_lower = (name or "").lower()
    summary_lower = (summary or "").lower()

    for pattern in _VAGUE_GOVERNMENT_PATTERNS:
        if pattern in name_lower:
            return True

    if name_lower in ("government policy update", "policy update", "vague_government_event"):
        return True

    has_gov_indicator = any(
        kw in summary_lower for kw in ("government", "legislat", "regulat", "subsid", "bill", "act", "policy")
    )
    if not has_gov_indicator:
        return False

    return False


async def _get_event_embeddings(event_names: list[str]) -> list[Any]:
    """Fetch embeddings for a list of event names."""
    try:
        return get_embeddings_batch(event_names)
    except Exception as e:
        logger.error(f"Failed to get embeddings for semantic grouping: {e}")
        return [None] * len(event_names)


def _group_events_semantically(
    events: list[MacroEvent], embeddings: list[Any], sim_threshold: float
) -> list[list[MacroEvent]]:
    """Group events based on semantic similarity of their names."""
    visited = [False] * len(events)
    groups = []

    for i in range(len(events)):
        if visited[i]:
            continue

        current_group = [events[i]]
        visited[i] = True

        for j in range(i + 1, len(events)):
            if visited[j]:
                continue

            is_similar = False
            if embeddings[i] and embeddings[j]:
                if cosine_similarity(embeddings[i], embeddings[j]) >= sim_threshold:
                    is_similar = True
            elif events[i].event_name.lower().strip() == events[j].event_name.lower().strip():
                is_similar = True

            if is_similar:
                current_group.append(events[j])
                visited[j] = True
        groups.append(current_group)
    return groups


async def _synthesize_and_promote_group(
    occurrences: list[MacroEvent], discovery_service: DiscoveryService, sim_threshold: float
):
    """Synthesize a group of events and promote to memory if consensus is reached."""
    unique_models = set()
    cumulative_weight = 0.0
    models_seen_for_weight = set()

    for occ in occurrences:
        model_key = f"{occ.model_provider}_{occ.model_name}"
        unique_models.add(model_key)
        if occ.model_name not in models_seen_for_weight:
            cumulative_weight += MODEL_WEIGHTS.get(occ.model_name, 1.0)
            models_seen_for_weight.add(occ.model_name)

    representative_name = occurrences[0].event_name

    # Combine reasoning and votes
    impact_weights = defaultdict(float)
    ongoing_votes, catalyst_votes = 0.0, 0.0
    parallels, scenarios, reasonings, source_ids, importance_scores = [], [], [], set(), []

    for occ in occurrences:
        weight = MODEL_WEIGHTS.get(occ.model_name, 1.0)
        impact_weights[occ.impact] += weight
        reasonings.append(occ.reasoning)
        source_ids.add(occ.source_id)
        importance_scores.append(occ.importance_score)

        if occ.is_ongoing:
            ongoing_votes += weight
        if occ.is_future_catalyst:
            catalyst_votes += weight
        if occ.historical_parallel:
            parallels.append(occ.historical_parallel)
        if getattr(occ, "scenario_analysis", None):
            scenarios.append(occ.scenario_analysis)

    majority_impact = _resolve_impact_tie(impact_weights)

    # --- LLM Synthesis ---
    synthesis = await synthesize_event(
        event_name=representative_name, impact=majority_impact, reasonings=reasonings, scenarios=scenarios
    )

    # Reject vague government events — they lack actionable specificity
    if _is_vague_government_event(synthesis["name"], synthesis.get("summary", "")):
        logger.warning(
            f"Rejecting vague government event from consensus: '{synthesis['name']}'. "
            "No specific bill, act, or regulation was identified."
        )
        return None

    is_ongoing = synthesis.get("is_ongoing", ongoing_votes > (cumulative_weight / 2))
    is_future_catalyst = synthesis.get("is_future_catalyst", catalyst_votes > (cumulative_weight / 2))
    historical_parallel = synthesis.get("historical_parallel") or (parallels[0] if parallels else None)

    # Discover real assets specifically per scenario
    scenarios_data = []
    global_discovered_assets = []
    seen_tickers = set()

    for s in synthesis.get("scenarios", []):
        header = s.get("cleanHeader", "")
        outcome = s.get("outcome", "")
        trading_plan = s.get("tradingPlan", "")

        # Discover assets specifically for this scenario's trading plan!
        theme = f"{header}: {outcome} -> Trading Plan: {trading_plan}"
        scenario_assets = await discovery_service.discover_assets(theme)

        # Add scenario tag and unique tickers to the global discovered list
        for asset in scenario_assets:
            asset["scenario"] = header
            ticker = asset["ticker"].upper()
            if ticker not in seen_tickers:
                global_discovered_assets.append(asset)
                seen_tickers.add(ticker)

        scenarios_data.append(
            {
                "cleanHeader": header,
                "percentage": s.get("percentage"),
                "outcome": outcome,
                "tradingPlan": trading_plan,
                "assets": scenario_assets,
            }
        )

    # For backward-compatibility fallback if no scenarios were returned by Gemini
    if not scenarios_data:
        # Fallback to old global discovery theme
        global_discovered_assets = await discovery_service.discover_assets(synthesis["summary"])

    scenario_analysis = synthesis.get("scenario_analysis") or ""
    # Format a clean string scenario_analysis for backward compatibility if structured scenarios exist
    if scenarios_data and not scenario_analysis:
        parts = []
        for s in scenarios_data:
            pct = s["percentage"]
            if pct and "probability" not in pct.lower():
                pct = f"{pct} probability"
            pct_str = f" ({pct})" if pct else ""
            parts.append(f"{s['cleanHeader']}{pct_str}: {s['outcome']} -> Trading Plan: {s['tradingPlan']}")
        scenario_analysis = " ".join(parts)

    if global_discovered_assets and scenario_analysis:
        asset_links = "\n\n**Investable Assets (via FMP):**\n"
        for asset in global_discovered_assets[:5]:
            asset_links += f"- ${asset['ticker']} ({asset['name']}): {asset['reason']}\n"
        scenario_analysis += asset_links

    consensus_data = {
        "event_name": synthesis["name"],
        "impact": majority_impact,
        "reasoning": synthesis["summary"],
        "models_involved": list(unique_models),
        "cumulative_weight": cumulative_weight,
        "source_ids": list(source_ids),
        "is_ongoing": is_ongoing,
        "is_future_catalyst": is_future_catalyst,
        "historical_parallel": historical_parallel,
        "future_date": synthesis.get("future_date"),
        "future_date_note": synthesis.get("future_date_note"),
        "scenario_analysis": scenario_analysis.strip() if scenario_analysis else None,
        "scenarios": scenarios_data,
        "discovered_assets": global_discovered_assets,
        "importance_score": synthesis.get(
            "importance_score", int(sum(importance_scores) / len(importance_scores)) if importance_scores else 5
        ),
    }

    # Analyze Relationship & Link Memory
    potential_parents = find_potential_ancestors(synthesis["summary"], threshold=0.4)
    relationship = await analyze_event_relationship(synthesis["summary"], potential_parents)

    parent_id = relationship.get("parent_id")
    rel_type = relationship.get("relationship_type")
    should_resolve = relationship.get("should_resolve", False)

    # Promote to long-term memory
    parallel_str = f" [Historical Parallel: {historical_parallel}]" if historical_parallel else ""
    ongoing_str = " [ONGOING]" if is_ongoing else ""
    memory_content = f"MARKET EVENT: {consensus_data['event_name']}{ongoing_str} | IMPACT: {consensus_data['impact']} | SUMMARY: {consensus_data['reasoning']}{parallel_str}"

    new_memory_id = add_memory(
        content=memory_content,
        metadata={
            "type": "consensus_event",
            "event_name": consensus_data["event_name"],
            "impact": consensus_data["impact"],
            "source_ids": consensus_data["source_ids"],
            "raw_name": representative_name,
            "cumulative_weight": cumulative_weight,
            "is_ongoing": is_ongoing,
            "is_future_catalyst": is_future_catalyst,
            "historical_parallel": historical_parallel,
            "future_date_note": consensus_data.get("future_date_note"),
            "scenario_analysis": consensus_data.get("scenario_analysis"),
            "scenarios": consensus_data.get("scenarios"),
            "discovered_assets": consensus_data.get("discovered_assets"),
            "importance_score": consensus_data["importance_score"],
            "participating_agents": list(unique_models),
            "models_involved": list(unique_models),
        },
        parent_id=parent_id,
        relationship_type=rel_type,
        target_date=consensus_data.get("future_date"),
        check_similarity=True,
        similarity_threshold=sim_threshold,
        lookback_hours=24,
    )

    if new_memory_id:
        logger.info(f"Promoted synthesized consensus event: {consensus_data['event_name']} (ID: {new_memory_id})")
        if should_resolve and parent_id:
            update_memory_status(parent_id, "RESOLVED")
            logger.info(f"Marked ancestor event {parent_id} as RESOLVED.")
        return consensus_data
    else:
        logger.warning(f"Failed to promote consensus event: {consensus_data['event_name']}")
    return None


async def process_consensus(
    events: list[MacroEvent], threshold: float = 2.0, sim_threshold: float = 0.75
) -> list[dict]:
    """Process a list of macro events and identify consensus using semantic grouping,
    deduplication, weighted voting, and LLM synthesis.

    Args:
        events: All MacroEvent objects generated by all models.
        threshold: Minimum cumulative weight of different models that must identify
            the same event for it to be promoted.
        sim_threshold: Cosine similarity threshold for semantic grouping.

    Returns:
        List of consensus events that were promoted to memory.
    """
    if not events:
        return []

    discovery_service = DiscoveryService()

    # 1. Batch generate embeddings for all event names
    embeddings = await _get_event_embeddings([e.event_name for e in events])

    # 2. Group events semantically
    if not embeddings or len(embeddings) != len(events):
        logger.warning(
            f"Embeddings list size mismatch: expected {len(events)}, got {len(embeddings) if embeddings else 0}. "
            "Falling back to exact string comparison for event grouping."
        )
        embeddings = [None] * len(events)

    groups = _group_events_semantically(events, embeddings, sim_threshold)

    consensus_reached = []

    # 3. Check each group for consensus
    for occurrences in groups:
        # Calculate cumulative weight for the group to check against threshold
        # We need to track which specific model (owner_id) we've already counted for weight
        models_seen_for_weight = set()
        cumulative_weight = 0.0
        for occ in occurrences:
            if occ.model_name not in models_seen_for_weight:
                weight = MODEL_WEIGHTS.get(occ.model_name, 1.0)
                cumulative_weight += weight
                models_seen_for_weight.add(occ.model_name)

        if cumulative_weight >= threshold:
            representative_name = occurrences[0].event_name
            unique_models = set(f"{occ.model_provider}_{occ.model_name}" for occ in occurrences)
            logger.info(
                f"Consensus reached on semantic event group: '{representative_name}' "
                f"(Models: {len(unique_models)}, Weight: {cumulative_weight:.2f})"
            )
            res = await _synthesize_and_promote_group(occurrences, discovery_service, sim_threshold)
            if res:
                consensus_reached.append(res)

    return consensus_reached


async def process_decision_consensus(decisions: list[DecisionObject]) -> list[dict]:
    """Consolidates trading decisions from multiple models for the same ticker/signal.

    Args:
        decisions: List of DecisionObject instances from different models.

    Returns:
        List of consolidated decision dictionaries.
    """
    if not decisions:
        return []

    # 1. Filter and group by (ticker, signal)
    # Skip HOLD signals as they don't require consolidation for execution
    groups = defaultdict(list)
    for d in decisions:
        if d.signal.upper() == "HOLD":
            continue
        key = (d.ticker.upper(), d.signal.upper())
        groups[key].append(d)

    consolidated_results = []

    # 2. Process each group
    for (ticker, signal), occurrences in groups.items():
        unique_models = set()
        reasonings = []
        strategies = []
        plannings = []
        source_ids = set()

        for occ in occurrences:
            model_key = f"{occ.model_provider}_{occ.model_name}"
            unique_models.add(model_key)
            reasonings.append(occ.reasoning)
            if getattr(occ, "strategy_reasoning", None):
                strategies.append(occ.strategy_reasoning)
            if getattr(occ, "advance_planning_notes", None):
                plannings.append(occ.advance_planning_notes)
            source_ids.add(occ.source_id)

        # Use the synthesis logic to create a unified reasoning for this decision
        # We include strategic intent and planning in the reasoning pool
        combined_perspectives = reasonings + strategies + plannings

        synthesis = await synthesize_event(
            event_name=f"{signal} signal for {ticker}",
            impact="BULLISH" if signal == "BUY" else "BEARISH",
            reasonings=combined_perspectives,
        )

        consolidated_results.append(
            {
                "ticker": ticker,
                "signal": signal,
                "models_involved": list(unique_models),
                "original_reasonings": reasonings,
                "synthesized_name": synthesis["name"],
                "synthesized_summary": synthesis["summary"],
                "source_ids": list(source_ids),
            }
        )

    return consolidated_results


if __name__ == "__main__":
    pass
