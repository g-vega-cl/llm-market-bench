"""Dynamic model discovery and pattern matching for live provider catalogs."""

import fnmatch
import time

import httpx

# Default allowlists for callers (e.g. unit tests) that invoke discovery without cfg.
_DEFAULT_ALLOWED_PATTERNS: dict[str, list[str]] = {
    "openrouter": ["*:free", "openrouter/free"],
    "kilo": ["*:free", "*-free", "kilo-auto/free"],
    "nous": ["*:free"],
}


def is_allowed_model(model: str, allowed_patterns: list[str] | None) -> bool:
    """True when ``model`` is a concrete ID permitted by ``allowed_patterns``."""
    cleaned = model.strip()
    if (
        not cleaned
        or cleaned.startswith((":", "-"))
        or any(ch in cleaned for ch in "*?[")
    ):
        return False
    if allowed_patterns is None:
        return True
    if not allowed_patterns:
        return False
    lowered = cleaned.lower()
    return any(fnmatch.fnmatch(lowered, p.lower()) for p in allowed_patterns)


def filter_allowed_models(
    models: list[str], allowed_patterns: list[str] | None
) -> list[str]:
    """Filters a live catalog down to concrete models matching ``allowed_patterns``."""
    if allowed_patterns is None:
        return models
    return [m for m in models if is_allowed_model(m, allowed_patterns)]


def filter_allowed_patterns(
    patterns: list[str], allowed_patterns: list[str] | None
) -> list[str]:
    """Filters pattern lists (may include globs) to entries scoped by allowlist."""
    if allowed_patterns is None:
        return patterns
    return [
        p
        for p in patterns
        if p != "*"
        and any(fnmatch.fnmatch(p.lower(), allow.lower()) for allow in allowed_patterns)
    ]


class ModelDiscovery:
    def __init__(
        self,
        cache_ttl_seconds: int = 3600,
        allowed_patterns_by_provider: dict[str, list[str]] | None = None,
    ):
        self.cache_ttl = cache_ttl_seconds
        # provider_id -> {"models": list[str], "expires_at": float}
        self._cache: dict[str, dict] = {}
        self._allowed_patterns: dict[str, list[str]] = (
            dict(allowed_patterns_by_provider)
            if allowed_patterns_by_provider is not None
            else dict(_DEFAULT_ALLOWED_PATTERNS)
        )

    def configure_allowed_patterns(self, providers: dict[str, dict]) -> None:
        """Replaces per-provider allowlists with those loaded from providers.json."""
        self._allowed_patterns = {
            p_id: list(p_cfg["allowed_model_patterns"])
            for p_id, p_cfg in providers.items()
            if p_cfg.get("allowed_model_patterns") is not None
        }

    def get_cached_models(self, provider_id: str) -> list[str] | None:
        entry = self._cache.get(provider_id)
        if entry and time.time() < entry["expires_at"]:
            return entry["models"]
        return None

    def set_cached_models(self, provider_id: str, models: list[str]) -> None:
        self._cache[provider_id] = {
            "models": models,
            "expires_at": time.time() + self.cache_ttl,
        }

    async def fetch_live_models(
        self,
        provider_id: str,
        base_url: str,
        headers: dict[str, str],
        client: httpx.AsyncClient | None = None,
    ) -> list[str]:
        """Queries provider's GET /models endpoint to discover live models."""
        cached = self.get_cached_models(provider_id)
        if cached is not None:
            return cached

        url = f"{base_url.rstrip('/')}/models"
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=httpx.Timeout(4.0, connect=2.0))
            should_close = True

        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                body = resp.json()
                raw_list = body if isinstance(body, list) else body.get("data", [])
                models = []
                for item in raw_list:
                    if isinstance(item, dict):
                        m_id = item.get("id") or item.get("name")
                        if m_id:
                            models.append(str(m_id))
                    elif isinstance(item, str):
                        models.append(item)
                if models:
                    patterns = self._allowed_patterns.get(provider_id)
                    models = filter_allowed_models(models, patterns)
                    self.set_cached_models(provider_id, models)
                    return models
        except Exception:
            pass
        finally:
            if should_close:
                await client.aclose()

        return []

    def match_best_model(
        self, candidate_models: list[str], patterns: list[str]
    ) -> str | None:
        """Finds the best model in candidate_models matching prioritized fnmatch patterns."""
        if not candidate_models:
            return None

        for pattern in patterns:
            for model in candidate_models:
                # Check case-insensitive pattern match
                if fnmatch.fnmatch(model.lower(), pattern.lower()):
                    return model

        # Fallback to the first candidate if no pattern matches
        return candidate_models[0]
