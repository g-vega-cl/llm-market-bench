import asyncio
import logging
from apps.engine.execution.market_data import MarketDataManager
from apps.engine.core.macro_tracker import get_global_macro_context
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

async def main():
    manager = MarketDataManager()
    result = await get_global_macro_context(manager)
    print("\nFINAL RESULT:")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
