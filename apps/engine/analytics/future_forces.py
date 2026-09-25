"""Future Forces & Forward Catalysts Analytics Engine.

Synthesizes, evaluates, and audits multi-horizon (2 to 24 months) market forces
across 7 canonical archetypes using OpenAI Luna (gpt-5.6-luna) with thinking:
1. Geopolitical & Chokepoints (Hormuz, Iran, Venezuela)
2. Government Agendas & Priorities (Defense appropriations, Replicator, CHIPS)
3. Sleeping Giants / Narrative Disconnects (Google valuation reconnection)
4. Latent Distribution Turn-On (Meta & open-weight model productization)
5. Inevitable Attack Surface Toll Roads (Cybersecurity in agentic AI)
6. Clinical-to-Cultural TAM Explosions (GLP-1s, preventative therapeutics)
7. Fixed Mega-Events & Contract Cliffs (2026 FIFA World Cup, aerospace cycles)
"""

from datetime import UTC, datetime
from typing import Any, Literal

import httpx
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from core import config
from core.config import logger

FutureForceArchetype = Literal[
    "geopolitical_chokepoint",
    "government_agenda",
    "sleeping_giant",
    "distribution_turnon",
    "secular_tollroad",
    "tam_explosion",
    "mega_event",
    "deep_value_turnaround",
]


class FutureForceCandidate(BaseModel):
    """Candidate future market force submitted for adversarial evaluation."""

    force_title: str = Field(..., description="High-conviction title of the force")
    archetype: FutureForceArchetype = Field(..., description="Structural archetype of the force")
    thesis: str = Field(..., description="Causal economic thesis explaining why the move is unpriced")
    catalyst_event: str = Field(..., description="Upcoming real-world milestone or event that triggers the move")
    horizon_months: int = Field(..., ge=2, le=24, description="Horizon floor is 2 months (60 days), max 24 months")
    target_date: str | None = Field(None, description="Expected realization date (YYYY-MM-DD)")
    invalidation_triggers: str = Field(..., description="Falsifiable criteria that immediately kill the thesis")
    transmission_mechanism: str = Field(
        ..., description="Financial mechanism converting the force into GAAP EPS or multiple expansion"
    )
    tickers: list[str] = Field(default_factory=list, description="Primary beneficiary or expression tickers")
    conviction_score: int = Field(default=4, ge=1, le=5, description="Initial conviction score (1 to 5)")


class ForceEvaluationResult(BaseModel):
    """Adversarial audit result produced by OpenAI Luna with thinking."""

    passes_rubric: bool = Field(..., description="Whether the force passes institutional rigor and rubric")
    conviction_score: int = Field(..., ge=1, le=5, description="Audited conviction score from 1 to 5")
    priced_in_assessment: str = Field(..., description="Critique of how much of this force is already priced in")
    critique: str = Field(..., description="Adversarial red-team critique and failure modes")
    recommended_horizon_months: int = Field(..., ge=2, le=24, description="Realistic timeframe for realization")
    falsification_clarity_score: int = Field(
        ..., ge=1, le=5, description="How crisp and testable the invalidation trigger is"
    )


class ForceAuditResult(BaseModel):
    """Sentinel audit result testing whether breaking news or data has killed an active thesis."""

    is_invalidated: bool = Field(..., description="True if explicit invalidation criteria have been triggered")
    is_realized: bool = Field(..., description="True if the catalyst occurred and full re-rating has played out")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the audit verdict")
    explanation: str = Field(..., description="Causal reasoning behind the invalidation or retention verdict")
    recommended_action: Literal["HOLD", "LIQUIDATE_INVALIDATED", "LIQUIDATE_REALIZED"] = Field(
        ..., description="Recommended portfolio execution action"
    )


# Baseline vetted future forces across canonical archetypes
DEFAULT_FUTURE_FORCES: list[dict[str, Any]] = [
    {
        "force_title": "Hormuz Energy & Tanker Squeeze",
        "archetype": "geopolitical_chokepoint",
        "tickers": ["FRO", "STNG", "FANG"],
        "horizon_months": 3,
        "thesis": (
            "Persistent naval escalation and maritime harassment in Persian Gulf chokepoint drives tanker day-rates up, "
            "while US Permian shale producers with zero maritime transit exposure capture high-margin geopolitical risk premiums."
        ),
        "catalyst_event": "Q3/Q4 VLCC tanker spot charter rate prints and EIA inventory drawing reports.",
        "invalidation_triggers": (
            "Formal international naval demilitarization treaty signed; free commercial passage restored; "
            "VLCC freight rates collapse >30% below trailing average."
        ),
        "transmission_mechanism": "High spot tanker freight rates flow straight to tanker free cash flow and dividend yields.",
        "conviction_score": 4,
    },
    {
        "force_title": "Autonomous Warfare & Defense Modernization",
        "archetype": "government_agenda",
        "tickers": ["AVAV", "KTOS", "HII"],
        "horizon_months": 6,
        "thesis": (
            "Pentagon Replicator initiative and NDAA statutory budget appropriations mandate mass deployment of uncrewed "
            "attritable aerial systems and autonomous naval craft, pivoting procurement away from legacy platforms."
        ),
        "catalyst_event": "DoD FY2027 defense appropriation markups and formal Replicator tranche production contract awards.",
        "invalidation_triggers": "Congressional defense budget caps slashed; Replicator program delayed or defunded in House Armed Services markup.",
        "transmission_mechanism": "Firm fixed-price production backlog conversion directly boosting quarterly revenue and operating margins.",
        "conviction_score": 5,
    },
    {
        "force_title": "The Sleeping Giant (Google Valuation Reconnection)",
        "archetype": "sleeping_giant",
        "tickers": ["GOOGL"],
        "horizon_months": 3,
        "thesis": (
            "Market severely mispriced Alphabet at trough forward P/E on transient LLM disruption panic, ignoring "
            "custom TPU hardware economics, DeepMind research supremacy, and Android/YouTube distribution locks."
        ),
        "catalyst_event": "Enterprise Google Cloud AI revenue acceleration and Search Generative Experience monetization prints.",
        "invalidation_triggers": "Sequential quarterly decline in Google Search ad revenues or DOJ court order forcing unbundled Android divestiture.",
        "transmission_mechanism": "Valuation multiple expansion from 18x to 24x+ forward P/E plus double-digit Cloud margin expansion.",
        "conviction_score": 5,
    },
    {
        "force_title": "Inevitable AI Threat Surface & Identity Toll Road",
        "archetype": "secular_tollroad",
        "tickers": ["CRWD", "PANW", "NET"],
        "horizon_months": 6,
        "thesis": (
            "Proliferation of autonomous AI coding agents expands enterprise software codebases and external API threat surfaces 10x; "
            "machine-speed synthetic cyber threats make real-time endpoint telemetry and Zero Trust identity non-discretionary compliance mandates."
        ),
        "catalyst_event": "Annual enterprise cyber budget reallocations and quarterly Net New ARR prints showing accelerated platform consolidation.",
        "invalidation_triggers": "Enterprise security budget growth stalls below 5% YoY; cloud giants commoditize endpoint behavioral detection.",
        "transmission_mechanism": "Contract expansions and platform bundle adoption driving >25% Free Cash Flow margin expansion.",
        "conviction_score": 5,
    },
    {
        "force_title": "FIFA World Cup 2026 Travel & Lodging Compression",
        "archetype": "mega_event",
        "tickers": ["ABNB", "BKNG"],
        "horizon_months": 9,
        "target_date": "2026-07-01",
        "thesis": (
            "The 2026 World Cup hosted across 16 North American metropolitan hubs creates unprecedented localized lodging demand "
            "exceeding hotel capacity, driving record Average Daily Rates (ADR) and booking volumes for flexible home rentals."
        ),
        "catalyst_event": "Advance ticket lottery distributions and Q1 2026 forward summer booking pace acceleration.",
        "invalidation_triggers": "Host cities enact emergency municipal bans on short-term rentals; event cancellation or major travel restrictions.",
        "transmission_mechanism": "Take-rate collection on surge ADR and gross booking value (GBV) surging during the tournament quarter.",
        "conviction_score": 4,
    },
]


def get_future_forces_openai_client(api_key: str | None = None) -> Any:
    """Instantiates instructor-wrapped AsyncOpenAI client."""
    key = api_key or config.OPENAI_API_KEY
    raw_client = AsyncOpenAI(api_key=key, timeout=httpx.Timeout(180.0))
    return instructor.from_openai(raw_client, mode=instructor.Mode.JSON)


def check_deterministic_invalidation(holding_data: dict[str, Any]) -> tuple[bool, str]:
    """Evaluates whether an existing holding has experienced deterministic thesis death."""
    if holding_data.get("is_bankrupt"):
        return True, "Company filed for bankruptcy or severe insolvency."
    if holding_data.get("is_delisted"):
        return True, "Stock was delisted from major US exchanges."
    if holding_data.get("thesis_canceled"):
        return True, "Underlying catalyst event explicitly canceled or declared void."

    # Date check: if target_date has passed by >30 days without positive re-rating
    target_date_str = holding_data.get("target_date")
    if target_date_str:
        try:
            target_date = datetime.strptime(str(target_date_str)[:10], "%Y-%m-%d").replace(tzinfo=UTC)
            now = datetime.now(UTC)
            if (now - target_date).days > 30 and float(holding_data.get("unrealized_pnl_usd") or 0.0) < 0:
                return (
                    True,
                    f"Target realization window expired on {target_date_str} without positive price resolution.",
                )
        except Exception as e:
            logger.debug("Could not parse target_date for invalidation check: %s", e)

    return False, "healthy"


async def evaluate_future_force(
    candidate: FutureForceCandidate,
    client: Any | None = None,
    model: str | None = None,
) -> ForceEvaluationResult:
    """Invokes gpt-5.6-luna with thinking to stress-test candidate force theses."""
    cl = client or get_future_forces_openai_client()
    target_model = model or config.OPENAI_MODEL

    prompt = (
        "You are Benchify's Chief Red-Team Investment Strategist.\n"
        "Critique and stress-test the following candidate Multi-Horizon Future Force (2 to 24 months):\n\n"
        f"Title: {candidate.force_title}\n"
        f"Archetype: {candidate.archetype}\n"
        f"Tickers: {', '.join(candidate.tickers)}\n"
        f"Horizon: {candidate.horizon_months} months\n"
        f"Thesis: {candidate.thesis}\n"
        f"Catalyst Event: {candidate.catalyst_event}\n"
        f"Invalidation Triggers: {candidate.invalidation_triggers}\n"
        f"Transmission Mechanism: {candidate.transmission_mechanism}\n\n"
        "Instructions:\n"
        "1. Is this already priced in by Wall Street consensus? (Check multiples and expectations).\n"
        "2. Does the transmission mechanism realistically convert into GAAP EPS or multiple re-rating within 2-24 months?\n"
        "3. Is the invalidation trigger crisp, testable, and falsifiable?\n"
        "Produce your structured evaluation."
    )

    kwargs: dict[str, Any] = {"reasoning_effort": "medium"} if "luna" in target_model.lower() else {}

    return await cl.chat.completions.create(
        model=target_model,
        response_model=ForceEvaluationResult,
        messages=[
            {
                "role": "system",
                "content": "You are an adversarial institutional investment committee evaluating asymmetric forward market forces.",
            },
            {"role": "user", "content": prompt},
        ],
        **kwargs,
    )


async def audit_force_invalidation(
    force_data: dict[str, Any],
    news_context: str,
    current_price: float | None = None,
    client: Any | None = None,
    model: str | None = None,
) -> ForceAuditResult:
    """Invokes gpt-5.6-luna with thinking to check if breaking news invalidates an active thesis."""
    # First check deterministic guardrails
    det_invalid, det_reason = check_deterministic_invalidation(force_data)
    if det_invalid:
        return ForceAuditResult(
            is_invalidated=True,
            is_realized=False,
            confidence=1.0,
            explanation=f"Deterministic failure: {det_reason}",
            recommended_action="LIQUIDATE_INVALIDATED",
        )

    cl = client or get_future_forces_openai_client()
    target_model = model or config.OPENAI_MODEL

    prompt = (
        "You are Benchify's Invalidation Sentinel Auditor. An investment thesis is active in our portfolio.\n"
        "Your task is to judge whether recent real-world news or developments have triggered the explicit Invalidation Criteria.\n\n"
        f"Force Title: {force_data.get('force_title')}\n"
        f"Archetype: {force_data.get('archetype')}\n"
        f"Tickers: {force_data.get('tickers')}\n"
        f"Original Thesis: {force_data.get('thesis')}\n"
        f"Explicit Invalidation Triggers: {force_data.get('invalidation_triggers')}\n"
        f"Catalyst Event: {force_data.get('catalyst_event')}\n"
        f"Current Market Price / Context: {current_price}\n\n"
        f"Recent News / Market Developments:\n{news_context}\n\n"
        "Audit Question:\n"
        "1. Did the news trigger the explicit invalidation criteria? If yes, set is_invalidated=True, recommended_action='LIQUIDATE_INVALIDATED'.\n"
        "2. Did the catalyst fully occur and reach target valuation? If yes, set is_realized=True, recommended_action='LIQUIDATE_REALIZED'.\n"
        "3. Otherwise, set recommended_action='HOLD'."
    )

    kwargs: dict[str, Any] = {"reasoning_effort": "medium"} if "luna" in target_model.lower() else {}

    return await cl.chat.completions.create(
        model=target_model,
        response_model=ForceAuditResult,
        messages=[
            {
                "role": "system",
                "content": "You are a disciplined portfolio risk officer enforcing strict thesis falsification rules.",
            },
            {"role": "user", "content": prompt},
        ],
        **kwargs,
    )


async def execute_get_future_forces_tool(
    archetype: str | None = None,
    max_horizon_months: int = 24,
    limit: int = 5,
) -> str:
    """Retrieves active future forces from DB (or fallback to default vetted list)."""
    forces = []
    try:
        from core.db import get_supabase_client

        client = get_supabase_client()
        query = client.table("future_forces").select("*").eq("status", "active")
        if archetype:
            query = query.eq("archetype", archetype.strip().lower())
        if max_horizon_months:
            query = query.lte("horizon_months", max_horizon_months)
        res = query.order("conviction_score", desc=True).limit(limit).execute()
        if res.data:
            forces = res.data
    except Exception as e:
        logger.debug("Could not fetch future_forces from database: %s", e)

    if not forces:
        # Fallback to vetted baseline
        forces = DEFAULT_FUTURE_FORCES
        if archetype:
            forces = [f for f in forces if f.get("archetype") == archetype.strip().lower()]
        if max_horizon_months:
            forces = [f for f in forces if f.get("horizon_months", 3) <= max_horizon_months]
        forces = forces[:limit]

    if not forces:
        return "No active future forces found matching the criteria."

    lines = [f"=== ACTIVE MULTI-HORIZON FORCES & CATALYSTS ({len(forces)}) ==="]
    for idx, f in enumerate(forces, 1):
        tickers_str = ", ".join(f.get("tickers") or [])
        lines.append(f"\n{idx}. [{f.get('archetype', 'UNKNOWN').upper()}] {f.get('force_title')}")
        lines.append(f"   • Expression Tickers: {tickers_str}")
        lines.append(f"   • Horizon: {f.get('horizon_months')} months | Conviction: {f.get('conviction_score', 4)}/5")
        if f.get("target_date"):
            lines.append(f"   • Target Date: {f.get('target_date')}")
        lines.append(f"   • Causal Thesis: {f.get('thesis')}")
        lines.append(f"   • Milestone Catalyst: {f.get('catalyst_event')}")
        lines.append(f"   • Transmission Mechanism: {f.get('transmission_mechanism')}")
        lines.append(f"   • Invalidation Criteria: {f.get('invalidation_triggers')}")

    return "\n".join(lines)


async def execute_research_future_force_tool(
    force_title: str,
    archetype: str,
    thesis: str,
    catalyst_event: str,
    invalidation_triggers: str,
    transmission_mechanism: str,
    tickers: list[str] | None = None,
    horizon_months: int = 3,
    model_name: str | None = None,
) -> str:
    """Stress-tests a candidate future force using OpenAI Luna with thinking."""
    try:
        candidate = FutureForceCandidate(
            force_title=force_title,
            archetype=archetype,  # type: ignore[arg-type]
            thesis=thesis,
            catalyst_event=catalyst_event,
            invalidation_triggers=invalidation_triggers,
            transmission_mechanism=transmission_mechanism,
            tickers=tickers or [],
            horizon_months=max(2, min(24, horizon_months)),
        )
        res = await evaluate_future_force(candidate, model=model_name)
        status_label = "PASSED RUBRIC" if res.passes_rubric else "FAILED RUBRIC"
        return (
            f"=== ADVERSARIAL FORCE AUDIT: {force_title} ({status_label}) ===\n"
            f"• Audited Conviction: {res.conviction_score}/5\n"
            f"• Recommended Horizon: {res.recommended_horizon_months} months\n"
            f"• Falsification Clarity: {res.falsification_clarity_score}/5\n"
            f"• Priced-In Assessment:\n  {res.priced_in_assessment}\n"
            f"• Red-Team Critique & Failure Modes:\n  {res.critique}"
        )
    except Exception as e:
        logger.exception("Error executing research_future_force tool: %s", e)
        return f"Error executing research_future_force: {str(e)}"
