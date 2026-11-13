"""Log-only unauthorized-request spike detection."""

from __future__ import annotations

import logging
import time
from collections import Counter, deque
from collections.abc import Callable
from dataclasses import dataclass

logger = logging.getLogger("free_llm_proxy.security")


@dataclass(frozen=True)
class UnauthorizedSpike:
    count: int
    window_seconds: int
    top_ips: list[tuple[str, int]]


class UnauthorizedMonitor:
    """Track 401s in a rolling window and log one warning per spike.

    This is intentionally in-memory and log-only: no network calls, no external
    alerting dependency. The persistent audit DB remains the source of truth for
    historical metrics.
    """

    def __init__(
        self,
        threshold: int = 20,
        window_seconds: int = 300,
        connector_id: str = "unknown",
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = threshold
        self.window_seconds = window_seconds
        self.connector_id = connector_id
        self._clock = clock
        self._events: deque[tuple[float, str]] = deque()
        self._alerted = False

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()
        if len(self._events) < self.threshold:
            self._alerted = False

    def record(self, client_ip: str | None) -> UnauthorizedSpike | None:
        if self.threshold <= 0:
            return None
        now = self._clock()
        self._events.append((now, client_ip or "unknown"))
        self._prune(now)
        if len(self._events) < self.threshold or self._alerted:
            return None

        self._alerted = True
        counts = Counter(ip for _, ip in self._events)
        spike = UnauthorizedSpike(
            count=len(self._events),
            window_seconds=self.window_seconds,
            top_ips=counts.most_common(3),
        )
        logger.warning(
            "security.401_spike connector=%s count=%d window=%ds top_ips=%s",
            self.connector_id,
            spike.count,
            spike.window_seconds,
            spike.top_ips,
        )
        return spike

    def count(self) -> int:
        if self.threshold <= 0:
            return 0
        self._prune(self._clock())
        return len(self._events)

    @property
    def alert_active(self) -> bool:
        return self.threshold > 0 and self.count() >= self.threshold

    def reset(self) -> None:
        self._events.clear()
        self._alerted = False
