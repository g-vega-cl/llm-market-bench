"""Dynamic model discovery and pattern matching for live provider catalogs."""

import fnmatch
import time
import httpx


class ModelDiscovery:
    def __init__(self, cache_ttl_seconds: int = 3600):
        self.cache_ttl = cache_ttl_seconds
        # provider_id -> {"models": list[str], "expires_at": float}
        self._cache: dict[str, dict] = {}

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
        if cached:
            return cached

        url = f"{base_url.rstrip('/')}/models"
        should_close = False
        if client is None:
            client = httpx.AsyncClient(timeout=10.0)
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
