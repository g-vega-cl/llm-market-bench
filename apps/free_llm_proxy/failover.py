"""Failover policy for the free-llm-proxy dispatch loop.

Pure policy, no I/O: everything here is a decision about *what to do next*,
which is what makes the never-unanswered contract testable without a socket.

The guarantee is deliberately precise: a **non-streaming** request ends in an
answer or a real error inside its own per-request budget (free segment plus
paid segment). Streams keep their unbounded relay semantics, because the head
of a stream is what an interactive caller is waiting on and cutting it loses
work that was already billed upstream.

One request-scoped deadline is enforced at *every* dispatch — the attempt loop
and the in-provider cascade both recompute what is left before firing — so no
provider can silently spend the budget several times over.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import time
from dataclasses import dataclass
from typing import Any

from apps.free_llm_proxy import config

logger = logging.getLogger("free_llm_proxy.failover")

# An attempt shorter than this is not worth dispatching: it would almost
# certainly be cancelled mid-flight, and the resulting 504 would cool a healthy
# provider for a harness deadline it had no part in.
MIN_ATTEMPT_SECONDS = 2.0


@dataclass(frozen=True)
class AttemptBudget:
    """What one dispatch may consume.

    ``skip`` means the request's budget for this segment is spent: do not
    dispatch at all. ``cap_s is None`` is an uncapped dispatch (Strata, or the
    kill switch). The two states are distinct fields rather than a magic float,
    so a caller cannot mistake "spent" for "zero seconds".
    """

    skip: bool = False
    cap_s: float | None = None


UNCAPPED = AttemptBudget()
SKIP = AttemptBudget(skip=True)


def segment_remaining_s(segment_started: float | None, deadline_s: float) -> float:
    """Seconds left in a request segment; ``inf`` when the deadline is disabled."""
    if deadline_s <= 0 or segment_started is None:
        return float("inf")
    return deadline_s - (time.perf_counter() - segment_started)


def attempt_budget(provider_cfg: dict[str, Any], remaining_s: float) -> AttemptBudget:
    """Cap for one attempt inside the segment that is currently spending.

    The free segment passes its own remaining budget, the paid segment passes
    the paid budget, so the sum of every attempt in a pass can never exceed
    ``FREE_PASS_DEADLINE_SECONDS + PAID_PASS_DEADLINE_SECONDS``.
    """
    base = config.CLOUD_REQUEST_TIMEOUT_SECONDS
    if base <= 0:
        return UNCAPPED
    declared = (
        config.PAID_ATTEMPT_TIMEOUT_SECONDS
        if provider_cfg.get("billing") == "paid"
        else config.FREE_ATTEMPT_TIMEOUT_SECONDS
    )
    cap = declared if declared > 0 else base
    if remaining_s < MIN_ATTEMPT_SECONDS:
        return SKIP
    return AttemptBudget(cap_s=min(base, cap, remaining_s))


def plan_models(
    provider_cfg: dict[str, Any], available_models: list[str] | None
) -> list[str]:
    """Catalog models covered by the provider's own plan, discovered live.

    Order follows ``free_model_patterns`` so the cheapest declared pattern wins
    first; model ids themselves are never hardcoded. An empty result is logged,
    because a renamed free model would otherwise turn a plan-included provider
    into "spend first" without a signal.
    """
    patterns = provider_cfg.get("free_model_patterns") or []
    picked: list[str] = []
    for pattern in patterns:
        for model in fnmatch.filter(available_models or [], pattern):
            if model not in picked:
                picked.append(model)
    if patterns and available_models and not picked:
        logger.warning(
            "Paid provider %s declares free_model_patterns %r but its live "
            "catalog matches none of them; every model on this provider is "
            "metered",
            provider_cfg.get("name", "?"),
            patterns,
        )
    return picked


def is_plan_model(provider_cfg: dict[str, Any], model: str) -> bool:
    """True when ``model`` is covered by the provider's plan, not metered."""
    return any(
        fnmatch.fnmatch(model, pattern)
        for pattern in (provider_cfg.get("free_model_patterns") or [])
    )


def last_resort_model(
    provider_cfg: dict[str, Any], available_models: list[str] | None
) -> str | None:
    """The single metered model this provider may spend on, grounded in the catalog.

    A retired or renamed pin must not turn every *-go request into a 502, so the
    caller falls back to the catalog-resolved model instead — still a model the
    provider's own ``GET /models`` listed, never an invented string.
    """
    wanted = str(provider_cfg.get("last_resort_model") or "").strip()
    if not wanted:
        return None
    for model in available_models or []:
        if model == wanted or model.endswith(f"/{wanted}"):
            return model
    logger.warning(
        "Paid provider %s declares last_resort_model %r but its live catalog "
        "does not list it; using the catalog-resolved model instead",
        provider_cfg.get("name", "?"),
        wanted,
    )
    return None


def opencode_go_attempts(
    provider_cfg: dict[str, Any],
    available_models: list[str] | None,
    resolved_model: str,
) -> list[tuple[str, bool]]:
    """Ordered ``(model, metered)`` attempts for a plan-bearing provider.

    Plan-included models first, then exactly one metered model: the pinned
    ``last_resort_model`` when the catalog still lists it, otherwise the
    catalog-resolved model. Never two metered models in one request.
    """
    attempts: list[tuple[str, bool]] = []
    for model in plan_models(provider_cfg, available_models):
        attempts.append((model, False))
    metered = last_resort_model(provider_cfg, available_models) or resolved_model
    if metered and metered not in [model for model, _ in attempts]:
        attempts.append((metered, not is_plan_model(provider_cfg, metered)))
    return attempts


FUTILE_RATE_LIMIT_HINTS = (
    "per day",
    "per-day",
    "perday",
    "tokens per day",
    "requests per day",
    "tpd",
    "free_tier_requests",
    "quota exceeded",
    "quota_exceeded",
    "current quota",
)


def is_futile_rate_limit(status_code: int, body: Any) -> bool:
    """True for a 429 that a same-provider retry cannot clear (daily/plan quota).

    A transient 429 is worth one adjacent model; a per-day quota wall, a TPD
    budget or an exhausted free-tier request count is not. The cascade re-checks
    this before *every* retry, not just once per provider, so a transient 429
    that turns into a quota wall does not keep burning attempts.
    """
    if status_code != 429:
        return False
    text = body if isinstance(body, str) else json.dumps(body, default=str)
    lowered = text.lower()
    return any(hint in lowered for hint in FUTILE_RATE_LIMIT_HINTS)


# Adjacent models worth trying on the *same* provider after a transient
# failure. A declarative table keeps the dispatch loop flat (Open/Closed): a new
# provider cascade is data, not another `if` ladder in the request handler.
IN_PROVIDER_CASCADES: dict[str, tuple[tuple[int, ...], tuple[str, ...]]] = {
    "gemini": (
        (429, 503),
        (
            "gemini-flash-latest",
            "gemini-3.8-flash",
            "gemini-3.6-flash",
            "gemini-3.5-flash",
        ),
    ),
    "openrouter": (
        (429, 503),
        (
            "openrouter/free",
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "nvidia/nemotron-3.5-super-vl:free",
            "nvidia/nemotron-3.5-lightning:free",
        ),
    ),
    "nvidia": (
        (404, 429, 503),
        (
            "minimaxai/minimax-m3.1-flash",
            "nvidia/nemotron-3.5-super-vl-120b-a12b",
            "nvidia/nemotron-3-ultra-550b-a55b",
            "mistralai/mistral-large-4-1t-a52b",
        ),
    ),
    "kilo": (
        (400, 401, 429, 503),
        (
            "kilo-auto/free",
            "reflection/beam-free",
            "nvidia/nemotron-3.5-super-vl:free",
        ),
    ),
}
