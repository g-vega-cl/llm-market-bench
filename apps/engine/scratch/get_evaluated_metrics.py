import asyncio
import os
import sys
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from autoresearch.evaluator import evaluate_week


async def main():
    report, metrics, baseline_tag = await evaluate_week(date(2026, 5, 18), date(2026, 5, 24))
    import json

    print("Computed metrics for 2026-05-18 to 2026-05-24:")
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
