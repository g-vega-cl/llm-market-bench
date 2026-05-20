import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import update_prices


async def background_task():
    start = time.time()
    await asyncio.sleep(0.5)
    end = time.time()
    return end - start

async def main():
    attempts = 0
    def mock_execute():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise Exception("Transient error")
        mock_data = MagicMock()
        mock_data.data = [{"owner_id": "user1"}]
        return mock_data

    mock_sb_client = MagicMock()
    mock_sb_client.table.return_value.select.return_value.execute = mock_execute

    with patch("update_prices.get_supabase_client", return_value=mock_sb_client), \
         patch("update_prices.is_transient_supabase_error", return_value=True), \
         patch("update_prices.MarketDataManager") as mock_mdm_cls, \
         patch("update_prices.initialize_with_retry") as mock_init:

        mock_mdm = mock_mdm_cls.return_value
        mock_mdm.is_market_open = AsyncMock(return_value=True)
        mock_mdm.get_quotes = AsyncMock(return_value={})
        mock_mdm.get_history = AsyncMock(return_value=[])

        mock_portfolio = MagicMock()
        mock_portfolio.owner_id = "user1"
        mock_portfolio.positions = {}
        mock_init.return_value = mock_portfolio

        start_time = time.time()

        # Run them concurrently
        bg_task = asyncio.create_task(background_task())
        main_task = asyncio.create_task(update_prices.update_prices())

        await main_task
        bg_elapsed = await bg_task

        total_time = time.time() - start_time

        print(f"Background task took: {bg_elapsed:.4f} seconds")
        print(f"Total time took: {total_time:.4f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
