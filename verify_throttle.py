import asyncio
import time
import sys
import os
from unittest.mock import AsyncMock, patch

# Add apps/engine to path
sys.path.append(os.path.abspath("apps/engine"))

from execution.providers.fmp import FMPProvider
import core.config

async def test_throttle():
    # Set throttle to 1 second
    core.config.FINANCIAL_API_THROTTLE_SECONDS = 1.0
    provider = FMPProvider()
    provider.api_key = "test_key"
    
    # Reset last call time
    FMPProvider._last_call_time = 0
    
    with patch("httpx.AsyncClient.get") as mock_get:
        from unittest.mock import MagicMock
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value=[{"price": 100.0, "marketCap": 1000.0}])
        mock_response.raise_for_status = MagicMock(return_value=None)
        mock_get.return_value = mock_response

        print("Starting first call...")
        start = time.time()
        await provider.get_ticker_data("AAPL")
        
        print("Starting second call (should wait ~1s)...")
        await provider.get_ticker_data("MSFT")
        end = time.time()
        
        duration = end - start
        print(f"Total duration for 2 calls: {duration:.2f}s")
        
        if duration >= 1.0:
            print("SUCCESS: Throttling works.")
        else:
            print("FAILURE: Throttling did not wait.")

if __name__ == "__main__":
    asyncio.run(test_throttle())
