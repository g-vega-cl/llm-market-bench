"""Circuit breaker and cooldown tracker for provider health and rate limits."""

import time


class CircuitBreaker:
    def __init__(self, default_cooldown_seconds: int = 60):
        self.default_cooldown = default_cooldown_seconds
        # provider_id -> cooldown_until_timestamp
        self._cooldowns: dict[str, float] = {}
        # provider_id -> consecutive_failures
        self._failures: dict[str, int] = {}
        # provider_id -> total_429_count
        self._rate_limit_hits: dict[str, int] = {}

    def is_healthy(self, provider_id: str) -> bool:
        """Checks if a provider is ready to receive requests (not in cooldown)."""
        cooldown_until = self._cooldowns.get(provider_id, 0.0)
        now = time.time()
        if now >= cooldown_until:
            if provider_id in self._cooldowns:
                del self._cooldowns[provider_id]
            return True
        return False

    def get_cooldown_remaining(self, provider_id: str) -> float:
        """Returns remaining cooldown in seconds, or 0.0 if healthy."""
        cooldown_until = self._cooldowns.get(provider_id, 0.0)
        remaining = cooldown_until - time.time()
        return max(0.0, round(remaining, 1))

    def record_failure(
        self,
        provider_id: str,
        status_code: int = 429,
        retry_after: float | str | None = None,
    ) -> None:
        """Records an error and trips the circuit breaker on 429 or repeated 5xx."""
        now = time.time()
        self._failures[provider_id] = self._failures.get(provider_id, 0) + 1

        if status_code == 429:
            self._rate_limit_hits[provider_id] = (
                self._rate_limit_hits.get(provider_id, 0) + 1
            )
            # Parse retry-after if provided
            cooldown = self.default_cooldown
            if retry_after is not None:
                try:
                    parsed = float(retry_after)
                    if parsed > 0:
                        cooldown = parsed
                except (ValueError, TypeError):
                    pass
            self._cooldowns[provider_id] = now + cooldown

        elif status_code >= 500:
            # Trip cooldown if 2 consecutive 5xx errors occur
            if self._failures[provider_id] >= 2:
                self._cooldowns[provider_id] = now + self.default_cooldown

    def record_success(self, provider_id: str) -> None:
        """Resets consecutive failure count on successful completion."""
        self._failures[provider_id] = 0

    def reset(self, provider_id: str) -> None:
        """Manually clears cooldown and failure status."""
        self._cooldowns.pop(provider_id, None)
        self._failures[provider_id] = 0

    def get_status_overview(self) -> dict[str, dict]:
        """Returns overview of all tracked providers for status/metrics."""
        all_providers = (
            set(self._cooldowns.keys())
            | set(self._failures.keys())
            | set(self._rate_limit_hits.keys())
        )
        overview = {}
        for prov in all_providers:
            remaining = self.get_cooldown_remaining(prov)
            overview[prov] = {
                "healthy": remaining == 0.0,
                "cooldown_remaining_sec": remaining,
                "consecutive_failures": self._failures.get(prov, 0),
                "rate_limit_hits": self._rate_limit_hits.get(prov, 0),
            }
        return overview
