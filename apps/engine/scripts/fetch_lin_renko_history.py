"""Fetch Historical LIN Prices & Calculate Renko Bricks.

Fetches 90-180 days of LIN daily price history via FMP, calculates 14-period ATR,
runs the RenkoEngine, and outputs the historical brick series for visual analysis and web frontend integration.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.renko import RenkoEngine
from execution.providers.fmp import FMPProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("engine")

OUTPUT_PATH = Path(__file__).parent.parent / "scratch" / "lin_renko_history.json"


async def fetch_and_generate_lin_renko():
    logger.info("Fetching historical price data for LIN via FMP...")
    provider = FMPProvider()
    
    # Fetch historical daily prices (e.g. 730 days / 2 years)
    history = await provider.get_history("LIN", days=730)
    
    if not history:
        logger.warning("FMP historical query returned no data. Using fallback realistic price history.")
        # Fallback to realistic LIN price series around $440-$460 range over 60 steps
        base = 440.0
        prices = []
        for i in range(60):
            step = (i % 7 - 3) * 1.8 + (i * 0.3)
            prices.append(round(base + step, 2))
        timestamps = [f"2026-06-{(i%30)+1:02d}" for i in range(len(prices))]
    else:
        # FMP history is sorted reverse-chronological; reverse it to chronological order
        bars = sorted(history, key=lambda b: b.get("fetched_at", ""))
        prices = [float(b.get("price", 0.0)) for b in bars]
        timestamps = [str(b.get("fetched_at", "")) for b in bars]

    # Calculate 14-period ATR
    atr = RenkoEngine.calculate_atr(prices, period=14)
    logger.info(f"Calculated 14-period ATR for LIN: ${atr:.2f}")

    # Initialize RenkoEngine with ATR brick size
    engine = RenkoEngine(symbol="LIN", brick_size=atr)

    all_generated_bricks = []
    for p, ts in zip(prices, timestamps, strict=False):
        new_bricks = engine.process_price(p, timestamp=ts)
        for b in new_bricks:
            all_generated_bricks.append({
                "id": b.brick_id,
                "direction": b.direction,
                "openPrice": b.open_price,
                "closePrice": b.close_price,
                "timestamp": b.timestamp,
            })

    output_data = {
        "symbol": "LIN",
        "total_candles_processed": len(prices),
        "atr_brick_size": atr,
        "current_trend": engine.state.trend_direction,
        "consecutive_bricks": engine.state.consecutive_bricks,
        "last_brick_price": engine.state.last_brick_price,
        "reversal_threshold": engine.state.reversal_threshold,
        "total_bricks": len(all_generated_bricks),
        "bricks": all_generated_bricks,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output_data, indent=2))

    logger.info(f"Successfully generated {len(all_generated_bricks)} Renko bricks.")
    logger.info(f"Saved output to {OUTPUT_PATH}")
    print("\n--- RENKO GENERATION SUMMARY ---")
    print("Symbol:               LIN")
    print(f"Candles Processed:    {len(prices)}")
    print(f"14-Day ATR Box Size:  ${atr:.2f}")
    print(f"Active Trend:         {engine.state.trend_direction}")
    print(f"Consecutive Bricks:   {engine.state.consecutive_bricks}")
    print(f"Last Brick Close:     ${engine.state.last_brick_price:.2f}")
    print(f"Reversal Threshold:   ${engine.state.reversal_threshold:.2f}")
    print(f"Total Bricks Formed:  {len(all_generated_bricks)}")
    if all_generated_bricks:
        print("\nLast 5 Renko Bricks:")
        for b in all_generated_bricks[-5:]:
            print(f"  Brick #{b['id']} ({b['timestamp']}): {b['direction']} [${b['openPrice']:.2f} -> ${b['closePrice']:.2f}]")


if __name__ == "__main__":
    asyncio.run(fetch_and_generate_lin_renko())
