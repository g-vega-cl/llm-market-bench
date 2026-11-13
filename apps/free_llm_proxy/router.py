"""Routing engine: tier waterfall, round-robin load balancing, and model resolution."""

import itertools
from typing import Any

from apps.free_llm_proxy import config
from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.discovery import ModelDiscovery

PAID_BILLING = "paid"


def estimate_prompt_tokens(messages: list[Any] | None) -> int:
    """Cheap ~4-chars-per-token estimate of a request's prompt size.

    Used only to skip providers whose documented context ceiling is below the
    prompt (e.g. groq 413s on prompts over ~8k tokens). A real tokenizer would
    be more accurate but adds a heavy dependency for a pre-dispatch filter; the
    estimate errs high on prose and low on code, so treat it as a lower bound.
    """
    if not messages:
        return 0
    total = 0
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content")
        else:
            content = getattr(msg, "content", None)
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    text = part.get("text")
                    if isinstance(text, str):
                        total += len(text)
    return total // 4


def _normalize_tier(raw: object, default: int = 2) -> int:
    """Coerces a hand-edited tier value into a safe, sortable integer."""
    try:
        tier = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return tier if tier >= 1 else default


def _is_strict_strata_target(model_lower: str) -> bool:
    return model_lower == "strata" or model_lower.startswith("strata/")


def _resolve_explicit_provider(
    requested_model: str,
    model_lower: str,
    active: dict[str, dict],
    is_strata_primary: bool,
) -> str | None:
    if "/" in requested_model:
        prefix = requested_model.split("/", 1)[0].lower()
        return prefix if prefix in active else None
    if model_lower in active:
        return model_lower
    if is_strata_primary and "strata" in active:
        return "strata"
    return None


def _tier_for_provider(
    p_id: str,
    p_cfg: dict,
    model_lower: str,
    explicit_provider: str | None,
    include_strata_in_auto: bool,
) -> int | None:
    """Returns the provider's tier for this request, or None when ineligible.

    Paid providers are fail-closed: they are only eligible when explicitly
    targeted or when the requested alias is listed in their ``auto_aliases``
    allowlist. The allowlist is authoritative, so a missing or edited
    ``enabled_in_auto`` flag cannot silently leak paid spend into free aliases.
    """
    is_paid = p_cfg.get("billing") == PAID_BILLING
    if is_paid:
        if p_id == explicit_provider:
            return 1
        if model_lower in p_cfg.get("auto_aliases", []):
            return _normalize_tier(p_cfg.get("tier"), default=3)
        return None

    if p_cfg.get("enabled_in_auto", True):
        return _normalize_tier(p_cfg.get("tier"), default=2)
    if p_id == "strata" and include_strata_in_auto:
        return 1
    if p_id == explicit_provider:
        return 1
    return None


class Router:
    def __init__(
        self,
        circuit_breaker: CircuitBreaker | None = None,
        discovery: ModelDiscovery | None = None,
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreaker(
            default_cooldown_seconds=config.DEFAULT_COOLDOWN
        )
        self.discovery = discovery or ModelDiscovery()
        self.config_data = config.load_providers_config()
        self.providers = self.config_data.get("providers", {})
        self.virtual_aliases = self.config_data.get("virtual_aliases", {})

        # Round-robin iterators for load balancing within tiers (created lazily)
        self._tier_counters: dict[int, itertools.count] = {}

    def get_active_providers(self) -> dict[str, dict]:
        """Filters providers to only those with valid credentials or no auth required."""
        active = {}
        for p_id, p_cfg in self.providers.items():
            req_auth = p_cfg.get("requires_auth", True)
            if not req_auth:
                active[p_id] = p_cfg
            else:
                env_key = p_cfg.get("env_key")
                key_val = config.get_provider_key(env_key)
                if key_val:
                    cfg_copy = dict(p_cfg)
                    cfg_copy["api_key"] = key_val
                    active[p_id] = cfg_copy
        return active

    def resolve_model_for_provider(
        self,
        provider_id: str,
        requested_model: str,
        available_models: list[str] | None = None,
    ) -> str:
        """Resolves requested model or alias to an actual model string on the provider."""
        # Generic local strata handling: use whichever model is live, or generic 'strata'
        if provider_id == "strata":
            if "/" in requested_model and requested_model.startswith("strata/"):
                stripped = requested_model.split("/", 1)[1]
                if available_models and stripped in available_models:
                    return stripped
                return stripped
            if available_models:
                if requested_model in available_models:
                    return requested_model
                return available_models[0]
            return "strata"

        p_cfg = self.providers.get(provider_id, {})
        preferred_patterns = p_cfg.get("preferred_patterns", ["*"])

        # OpenRouter safety guard: strictly filter available models to free tier
        if provider_id == "openrouter":
            if available_models:
                available_models = [
                    m
                    for m in available_models
                    if m.endswith(":free") or m == "openrouter/free"
                ]
            preferred_patterns = [
                p
                for p in preferred_patterns
                if p.endswith(":free") or p == "openrouter/free"
            ] or ["openrouter/free"]

        # Kilo Code safety guard: strictly filter available models to free tier
        if provider_id == "kilo":
            if available_models:
                available_models = [
                    m
                    for m in available_models
                    if m.endswith(":free")
                    or m.endswith("-free")
                    or m == "kilo-auto/free"
                ]
            preferred_patterns = [
                p
                for p in preferred_patterns
                if p.endswith(":free") or p.endswith("-free") or p == "kilo-auto/free"
            ] or ["kilo-auto/free"]

        # Gemini safety guard: strictly filter available models to modern free Flash tier
        if provider_id == "gemini":
            if available_models:
                available_models = [
                    m
                    for m in available_models
                    if "flash" in m.lower()
                    and not any(
                        v in m
                        for v in (
                            "-1.5",
                            "-2.0",
                            "-2.5",
                            "-2-",
                            "-1-",
                            "1.5",
                            "2.0",
                            "2.5",
                        )
                    )
                ]

        # Check virtual alias patterns first
        if requested_model in self.virtual_aliases:
            patterns = self.virtual_aliases[requested_model]
        elif requested_model in {"default", "auto", ""}:
            patterns = self.virtual_aliases.get("auto-strata", preferred_patterns)
        elif requested_model in preferred_patterns:
            return requested_model.replace("*", "").strip()
        elif available_models and requested_model in available_models:
            return requested_model
        elif "/" in requested_model and requested_model.startswith(f"{provider_id}/"):
            # Explicit provider prefix passed by client: strip prefix
            stripped = requested_model.split("/", 1)[1]
            if provider_id == "openrouter":
                if (
                    requested_model == "openrouter/free"
                    or stripped == "openrouter/free"
                ):
                    return "openrouter/free"
                if not stripped.endswith(":free"):
                    # Non-free model requested for OpenRouter: strictly disallow and fall back
                    return "openrouter/free"
            if provider_id == "gemini" and (
                "flash" not in stripped.lower()
                or any(
                    v in stripped
                    for v in ("-1.5", "-2.0", "-2.5", "-2-", "-1-", "1.5", "2.0", "2.5")
                )
            ):
                flash_candidates = (
                    [m for m in (available_models or []) if "flash" in m.lower()]
                    if available_models
                    else []
                )
                matched = (
                    self.discovery.match_best_model(
                        flash_candidates, preferred_patterns
                    )
                    if flash_candidates
                    else (
                        flash_candidates[0]
                        if flash_candidates
                        else "gemini-flash-latest"
                    )
                )
                return (matched or "gemini-flash-latest").replace("*", "").strip()
            if available_models:
                if stripped in available_models:
                    return stripped
                for m in available_models:
                    if m.endswith(f"/{stripped}") or m.endswith(stripped):
                        return m
            return stripped
        else:
            # Check if requested model exists directly in provider's live models
            if (
                available_models
                and requested_model in available_models
                and not (
                    provider_id == "gemini"
                    and (
                        "flash" not in requested_model.lower()
                        or any(
                            v in requested_model
                            for v in (
                                "-1.5",
                                "-2.0",
                                "-2.5",
                                "-2-",
                                "-1-",
                                "1.5",
                                "2.0",
                                "2.5",
                            )
                        )
                    )
                )
            ):
                return requested_model
            # Otherwise treat as generic request -> fall back to preferred patterns
            patterns = preferred_patterns

        candidates = available_models or preferred_patterns
        best = self.discovery.match_best_model(candidates, patterns)
        resolved = best or (candidates[0] if candidates else requested_model)
        if provider_id == "openrouter" and not (
            resolved.endswith(":free") or resolved == "openrouter/free"
        ):
            return "openrouter/free"
        if provider_id == "kilo" and not (
            resolved.endswith(":free")
            or resolved.endswith("-free")
            or resolved == "kilo-auto/free"
        ):
            return "kilo-auto/free"
        if provider_id == "gemini":
            is_legacy = any(
                v in resolved
                for v in ("-1.5", "-2.0", "-2.5", "-2-", "-1-", "1.5", "2.0", "2.5")
            )
            if "flash" not in resolved.lower() or is_legacy:
                flash_candidates = (
                    [m for m in (available_models or []) if "flash" in m.lower()]
                    if available_models
                    else []
                )
                matched = (
                    self.discovery.match_best_model(
                        flash_candidates, preferred_patterns
                    )
                    if flash_candidates
                    else (
                        flash_candidates[0]
                        if flash_candidates
                        else "gemini-flash-latest"
                    )
                )
                resolved = matched or "gemini-flash-latest"
        return resolved.replace("*", "").strip()

    def get_candidate_chain(
        self, requested_model: str, prompt_tokens: int | None = None
    ) -> list[tuple[str, dict]]:
        """Returns ordered list of (provider_id, provider_cfg) to attempt for a request.

        Prioritizes Tier 1 healthy providers (round-robin balanced),
        then Tier 2 healthy providers. If all are in cooldown, includes
        cooling-down providers as last resort.
        """
        active = self.get_active_providers()
        if not active:
            return []

        model_lower = requested_model.lower().strip()

        # Strict local Strata targeting (never falls back to free pool)
        if _is_strict_strata_target(model_lower):
            if "strata" in active:
                return [("strata", active["strata"])]
            return []

        include_strata_in_auto = model_lower in {
            "auto-strata",
            "auto-strata-go",
            "free-auto-strata",
            "default",
            "auto",
            "",
        }
        is_strata_primary = model_lower in {"strata-auto", "strata-auto-go"}

        # If client explicitly specified a provider (e.g. 'groq/qwen...' or 'openrouter')
        explicit_provider = _resolve_explicit_provider(
            requested_model, model_lower, active, is_strata_primary
        )

        free_buckets: dict[int, list[tuple[str, dict]]] = {}
        paid_buckets: dict[int, list[tuple[str, dict]]] = {}

        for p_id, p_cfg in active.items():
            # Skip providers whose documented context ceiling is below this prompt.
            # A 413 on a big prompt is deterministic; excluding before dispatch
            # avoids a guaranteed-wasted round trip on every oversized request.
            max_prompt = p_cfg.get("max_prompt_tokens")
            if (
                prompt_tokens is not None
                and isinstance(max_prompt, int)
                and prompt_tokens > max_prompt
            ):
                continue
            tier = _tier_for_provider(
                p_id, p_cfg, model_lower, explicit_provider, include_strata_in_auto
            )
            if tier is None:
                continue
            buckets = (
                paid_buckets if p_cfg.get("billing") == PAID_BILLING else free_buckets
            )
            buckets.setdefault(tier, []).append((p_id, p_cfg))

        # Rotate healthy candidates within each tier using round-robin offset
        def balance_tier(
            candidates: list[tuple[str, dict]], tier_num: int
        ) -> list[tuple[str, dict]]:
            if not candidates:
                return []
            counter = self._tier_counters.setdefault(tier_num, itertools.count())
            idx = next(counter) % len(candidates)
            return candidates[idx:] + candidates[:idx]

        def build_segments(
            buckets: dict[int, list[tuple[str, dict]]],
        ) -> tuple[list[tuple[str, dict]], list[tuple[str, dict]]]:
            balanced = []
            for tier_num in sorted(buckets):
                balanced.extend(balance_tier(buckets[tier_num], tier_num))

            healthy: list[tuple[str, dict]] = []
            cooling: list[tuple[str, dict]] = []
            for candidate in balanced:
                if self.circuit_breaker.is_healthy(candidate[0]):
                    healthy.append(candidate)
                else:
                    cooling.append(candidate)
            return healthy, cooling

        free_healthy, free_cooling = build_segments(free_buckets)
        paid_healthy, paid_cooling = build_segments(paid_buckets)

        # If explicit provider was requested, move it to the front within its segment
        if explicit_provider:
            for segment in (free_healthy, free_cooling, paid_healthy, paid_cooling):
                segment.sort(key=lambda x: 0 if x[0] == explicit_provider else 1)

        explicit_is_paid = (
            explicit_provider is not None
            and active[explicit_provider].get("billing") == PAID_BILLING
        )
        if explicit_is_paid:
            return paid_healthy + paid_cooling + free_healthy + free_cooling

        if paid_healthy or paid_cooling:
            # Free cooling candidates stay ahead of paid ones: a rate-limit storm
            # must never turn the *-go aliases into paid-only routing.
            return free_healthy + free_cooling + paid_healthy + paid_cooling

        # Free-only aliases keep the existing behavior: cooling is a last resort.
        return free_healthy if free_healthy else free_cooling
