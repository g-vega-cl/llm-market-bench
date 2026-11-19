"""Routing engine: tier waterfall, round-robin load balancing, and model resolution."""

import itertools
from typing import Any

from apps.free_llm_proxy import config
from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.discovery import (
    ModelDiscovery,
    filter_allowed_models,
    filter_allowed_patterns,
    is_allowed_model,
)

PAID_BILLING = "paid"
_LEGACY_GEMINI_MARKERS = ("-1.5", "-2.0", "-2.5", "-2-", "-1-", "1.5", "2.0", "2.5")


def _is_modern_gemini_flash(model: str) -> bool:
    return "flash" in model.lower() and not any(
        v in model for v in _LEGACY_GEMINI_MARKERS
    )


def _resolve_strata_model(
    requested_model: str, available_models: list[str] | None
) -> str:
    if requested_model.lower().startswith("strata/"):
        return requested_model.split("/", 1)[1]
    if available_models:
        if requested_model in available_models:
            return requested_model
        return available_models[0]
    return "strata"


def _filter_provider_candidates(
    provider_id: str, p_cfg: dict, available_models: list[str] | None
) -> tuple[list[str] | None, list[str]]:
    preferred_patterns = list(p_cfg.get("preferred_patterns", ["*"]))
    allowed = p_cfg.get("allowed_model_patterns")
    if allowed is not None:
        if available_models is not None:
            available_models = filter_allowed_models(available_models, allowed)
        preferred_patterns = filter_allowed_patterns(preferred_patterns, allowed)
        dyn = p_cfg.get("dynamic_fallback_model")
        if not preferred_patterns and dyn:
            preferred_patterns = [dyn]
    if provider_id == "gemini" and available_models:
        available_models = [m for m in available_models if _is_modern_gemini_flash(m)]
    return available_models, preferred_patterns


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
        self.discovery.configure_allowed_patterns(self.providers)

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

    def _fallback_model(
        self,
        provider_id: str,
        p_cfg: dict,
        available_models: list[str] | None,
        preferred_patterns: list[str],
    ) -> str:
        if provider_id == "gemini":
            flash_models = [
                m for m in (available_models or []) if _is_modern_gemini_flash(m)
            ]
            matched = (
                self.discovery.match_best_model(flash_models, preferred_patterns)
                if flash_models
                else None
            )
            return (matched or "gemini-flash-latest").replace("*", "").strip()

        allowed = p_cfg.get("allowed_model_patterns")
        if allowed is not None:
            if available_models:
                matched = self.discovery.match_best_model(
                    available_models, preferred_patterns
                )
                if matched and is_allowed_model(matched, allowed):
                    return matched
            dyn = p_cfg.get("dynamic_fallback_model") or ""
            return dyn if is_allowed_model(dyn, allowed) else ""

        matched = self.discovery.match_best_model(
            available_models or preferred_patterns, preferred_patterns
        )
        return (matched or "").replace("*", "").strip()

    def _resolve_prefixed_model(
        self,
        provider_id: str,
        p_cfg: dict,
        requested_model: str,
        available_models: list[str] | None,
        preferred_patterns: list[str],
    ) -> str:
        stripped = requested_model.split("/", 1)[1].strip()
        allowed = p_cfg.get("allowed_model_patterns")
        if (
            provider_id == "openrouter"
            and stripped.lower() == "free"
            and (allowed is None or is_allowed_model("openrouter/free", allowed))
        ):
            return "openrouter/free"

        disallowed_marketplace = allowed is not None and not is_allowed_model(
            stripped, allowed
        )
        disallowed_gemini = provider_id == "gemini" and not _is_modern_gemini_flash(
            stripped
        )
        if disallowed_marketplace or disallowed_gemini:
            return self._fallback_model(
                provider_id, p_cfg, available_models, preferred_patterns
            )

        if available_models:
            if stripped in available_models:
                return stripped
            for candidate in available_models:
                if candidate.endswith(f"/{stripped}"):
                    return candidate
            if allowed is not None:
                return self._fallback_model(
                    provider_id, p_cfg, available_models, preferred_patterns
                )
        elif allowed is not None:
            return self._fallback_model(
                provider_id, p_cfg, available_models, preferred_patterns
            )
        return stripped

    def _finalize_resolved_model(
        self,
        provider_id: str,
        p_cfg: dict,
        resolved: str,
        available_models: list[str] | None,
        preferred_patterns: list[str],
    ) -> str:
        cleaned = resolved.replace("*", "").strip()
        allowed = p_cfg.get("allowed_model_patterns")
        if allowed is not None and not is_allowed_model(cleaned, allowed):
            return self._fallback_model(
                provider_id, p_cfg, available_models, preferred_patterns
            )
        if provider_id == "gemini" and not _is_modern_gemini_flash(cleaned):
            return self._fallback_model(
                provider_id, p_cfg, available_models, preferred_patterns
            )
        return cleaned

    def resolve_model_for_provider(
        self,
        provider_id: str,
        requested_model: str,
        available_models: list[str] | None = None,
    ) -> str:
        """Resolves requested model or alias to a safe model ID on the provider."""
        if provider_id == "strata":
            return _resolve_strata_model(requested_model, available_models)

        p_cfg = self.providers.get(provider_id, {})
        available_models, preferred_patterns = _filter_provider_candidates(
            provider_id, p_cfg, available_models
        )

        if requested_model in self.virtual_aliases:
            patterns = self.virtual_aliases[requested_model]
        elif requested_model in {"default", "auto", ""}:
            patterns = self.virtual_aliases.get("auto-strata", preferred_patterns)
        elif available_models and requested_model in available_models:
            return self._finalize_resolved_model(
                provider_id,
                p_cfg,
                requested_model,
                available_models,
                preferred_patterns,
            )
        elif requested_model.lower().startswith(f"{provider_id.lower()}/"):
            return self._resolve_prefixed_model(
                provider_id,
                p_cfg,
                requested_model,
                available_models,
                preferred_patterns,
            )
        else:
            patterns = preferred_patterns

        if p_cfg.get("allowed_model_patterns") is not None and not available_models:
            return self._fallback_model(
                provider_id, p_cfg, available_models, preferred_patterns
            )

        candidates = available_models or preferred_patterns
        best = (
            self.discovery.match_best_model(candidates, patterns)
            if candidates
            else None
        )
        resolved = best or (candidates[0] if candidates else "")
        return self._finalize_resolved_model(
            provider_id, p_cfg, resolved, available_models, preferred_patterns
        )

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
