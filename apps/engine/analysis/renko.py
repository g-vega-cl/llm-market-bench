"""Renko Chart Engine with ATR Sizing & Reversal Threshold Logic.

Implements discrete Renko brick calculation, trend tracking, and reversal thresholds
for quantitative trading strategies.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal


@dataclass
class RenkoBrick:
    """Represents a single Renko brick."""

    brick_id: int
    direction: Literal["UP", "DOWN"]
    open_price: float
    close_price: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class RenkoState:
    """Represents current Renko chart state for LLM context injection."""

    trend_direction: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "NEUTRAL"
    last_brick_price: float = 0.0
    reversal_threshold: float = 0.0
    consecutive_bricks: int = 0
    brick_size: float = 2.0


class RenkoEngine:
    """Renko calculation engine supporting dynamic ATR or fixed box sizing."""

    def __init__(self, symbol: str, brick_size: float = 2.0):
        self.symbol = symbol
        self.brick_size = max(float(brick_size), 0.01)
        self.bricks: list[RenkoBrick] = []
        self.state = RenkoState(brick_size=self.brick_size)
        self._anchor_price: float | None = None

    @staticmethod
    def calculate_atr(prices: list[float], period: int = 14) -> float:
        """Calculates Average True Range (ATR) snapshot from price series."""
        if len(prices) < 2:
            return 2.0
        
        diffs = [abs(prices[i] - prices[i - 1]) for i in range(1, len(prices))]
        if not diffs:
            return 2.0
        
        recent_diffs = diffs[-period:] if len(diffs) >= period else diffs
        atr = sum(recent_diffs) / len(recent_diffs)
        return max(round(atr, 2), 0.10)

    def process_price(self, price: float, timestamp: str | None = None) -> list[RenkoBrick]:
        """Processes a new price tick and returns any newly formed Renko bricks."""
        price = float(price)
        timestamp = timestamp or datetime.now(UTC).isoformat()
        new_bricks: list[RenkoBrick] = []

        if self._anchor_price is None:
            self._anchor_price = price
            self.state.last_brick_price = price
            self.state.reversal_threshold = price
            return new_bricks

        last_p = self.state.last_brick_price

        if self.state.trend_direction in ("BULLISH", "NEUTRAL"):
            # Check for UP continuation brick(s)
            while price >= last_p + self.brick_size:
                next_close = last_p + self.brick_size
                brick = RenkoBrick(
                    brick_id=len(self.bricks) + 1,
                    direction="UP",
                    open_price=last_p,
                    close_price=next_close,
                    timestamp=timestamp,
                )
                self.bricks.append(brick)
                new_bricks.append(brick)
                last_p = next_close
                self.state.trend_direction = "BULLISH"
                self.state.consecutive_bricks += 1

            # Check for 2-brick DOWN reversal
            reversal_price = self.state.last_brick_price - (2 * self.brick_size)
            if price <= reversal_price:
                # 2-brick reversal triggered
                last_p = self.state.last_brick_price
                while price <= last_p - self.brick_size:
                    next_close = last_p - self.brick_size
                    brick = RenkoBrick(
                        brick_id=len(self.bricks) + 1,
                        direction="DOWN",
                        open_price=last_p,
                        close_price=next_close,
                        timestamp=timestamp,
                    )
                    self.bricks.append(brick)
                    new_bricks.append(brick)
                    last_p = next_close

                self.state.trend_direction = "BEARISH"
                self.state.consecutive_bricks = len(new_bricks)

        elif self.state.trend_direction == "BEARISH":
            # Check for DOWN continuation brick(s)
            while price <= last_p - self.brick_size:
                next_close = last_p - self.brick_size
                brick = RenkoBrick(
                    brick_id=len(self.bricks) + 1,
                    direction="DOWN",
                    open_price=last_p,
                    close_price=next_close,
                    timestamp=timestamp,
                )
                self.bricks.append(brick)
                new_bricks.append(brick)
                last_p = next_close
                self.state.consecutive_bricks += 1

            # Check for 2-brick UP reversal
            reversal_price = self.state.last_brick_price + (2 * self.brick_size)
            if price >= reversal_price:
                # 2-brick reversal triggered
                last_p = self.state.last_brick_price
                while price >= last_p + self.brick_size:
                    next_close = last_p + self.brick_size
                    brick = RenkoBrick(
                        brick_id=len(self.bricks) + 1,
                        direction="UP",
                        open_price=last_p,
                        close_price=next_close,
                        timestamp=timestamp,
                    )
                    self.bricks.append(brick)
                    new_bricks.append(brick)
                    last_p = next_close

                self.state.trend_direction = "BULLISH"
                self.state.consecutive_bricks = len(new_bricks)

        # Update state last price and reversal threshold
        if new_bricks:
            self.state.last_brick_price = last_p
            if self.state.trend_direction == "BULLISH":
                self.state.reversal_threshold = last_p - (2 * self.brick_size)
            else:
                self.state.reversal_threshold = last_p + (2 * self.brick_size)

        return new_bricks
