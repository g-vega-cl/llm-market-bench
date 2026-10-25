"""Routing engine: tier waterfall, round-robin load balancing, and model resolution."""

import itertools
from apps.free_llm_proxy import config
from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.discovery import ModelDiscovery


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

        # Round-robin iterators for load balancing within tiers
        self._tier_counters: dict[int, itertools.count] = {
            1: itertools.count(),
            2: itertools.count(),
        }

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
        p_cfg = self.providers.get(provider_id, {})
        preferred_patterns = p_cfg.get("preferred_patterns", ["*"])

        # Check virtual alias patterns first
        if requested_model in self.virtual_aliases:
            patterns = self.virtual_aliases[requested_model]
        elif requested_model in {"default", "auto", ""}:
            patterns = self.virtual_aliases.get("free-auto", preferred_patterns)
        elif "/" in requested_model and requested_model.startswith(f"{provider_id}/"):
            # Explicit provider prefix passed by client: strip prefix
            stripped = requested_model.split("/", 1)[1]
            if available_models:
                if stripped in available_models:
                    return stripped
                for m in available_models:
                    if m.endswith(f"/{stripped}") or m.endswith(stripped):
                        return m
            return stripped
        else:
            # Check if requested model exists directly in provider's live models
            if available_models and requested_model in available_models:
                return requested_model
            # Otherwise treat as generic request -> fall back to preferred patterns
            patterns = preferred_patterns

        candidates = available_models or preferred_patterns
        best = self.discovery.match_best_model(candidates, patterns)
        return best or (candidates[0] if candidates else requested_model)

    def get_candidate_chain(self, requested_model: str) -> list[tuple[str, dict]]:
        """Returns ordered list of (provider_id, provider_cfg) to attempt for a request.

        Prioritizes Tier 1 healthy providers (round-robin balanced),
        then Tier 2 healthy providers. If all are in cooldown, includes
        cooling-down providers as last resort.
        """
        active = self.get_active_providers()
        if not active:
            return []

        # If client explicitly specified a provider (e.g. 'groq/qwen...')
        explicit_provider = None
        if "/" in requested_model:
            prefix = requested_model.split("/", 1)[0].lower()
            if prefix in active:
                explicit_provider = prefix

        tier1 = []
        tier2 = []

        for p_id, p_cfg in active.items():
            tier = p_cfg.get("tier", 2)
            if tier == 1:
                tier1.append((p_id, p_cfg))
            else:
                tier2.append((p_id, p_cfg))

        # Rotate healthy candidates within each tier using round-robin offset
        def balance_tier(
            candidates: list[tuple[str, dict]], tier_num: int
        ) -> list[tuple[str, dict]]:
            if not candidates:
                return []
            idx = next(self._tier_counters[tier_num]) % len(candidates)
            return candidates[idx:] + candidates[:idx]

        balanced_t1 = balance_tier(tier1, 1)
        balanced_t2 = balance_tier(tier2, 2)

        # Separate healthy vs cooling-down candidates
        healthy_chain = []
        cooling_chain = []

        for p_id, p_cfg in balanced_t1 + balanced_t2:
            if self.circuit_breaker.is_healthy(p_id):
                healthy_chain.append((p_id, p_cfg))
            else:
                cooling_chain.append((p_id, p_cfg))

        # If explicit provider was requested, move it to the front
        if explicit_provider:
            healthy_chain.sort(key=lambda x: 0 if x[0] == explicit_provider else 1)

        # Fall back to cooling providers only if no healthy candidates remain
        return healthy_chain if healthy_chain else cooling_chain
