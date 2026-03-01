import httpx
import asyncio
import sys

# --- Configuration ---
# 1. Use the same key you put in apps/ibkr-proxy/.env
API_KEY = "your-secret-key-123" 

# 2. Test both local and remote URLs
URLS = [
    "https://clvg.uk",
    "http://localhost:8000",
]

async def test_endpoint(url):
    print(f"\n--- Testing: {url} ---")
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Test Health Check
        try:
            resp = await client.get(f"{url}/", timeout=10)
            print(f"Index Status: {resp.status_code}")
            print(f"Index Payload: {resp.json()}")
        except Exception as e:
            print(f"Index Error: {e}")

        # 2. Test Price Fetch (AAPL)
        try:
            print(f"Fetching Price for AAPL...")
            resp = await client.get(f"{url}/price/AAPL", headers=headers, timeout=15)
            if resp.status_code == 200:
                print(f"SUCCESS! AAPL Price: {resp.json().get('price')}")
            else:
                print(f"FAILED Status: {resp.status_code}")
                print(f"Detail: {resp.text}")
        except Exception as e:
            print(f"Price Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_endpoint(sys.argv[1] if len(sys.argv) > 1 else URLS[0]))
    # If the first one worked, you can try the second one manually:
    # python test_proxy.py https://clvg.uk
