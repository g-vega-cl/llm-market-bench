import asyncio
from ib_async import IB
import os
from dotenv import load_dotenv

load_dotenv()

async def test_tws():
    ib = IB()
    host = os.getenv("IBKR_HOST", "127.0.0.1")
    port = int(os.getenv("IBKR_PORT", "7496"))
    client_id = int(os.getenv("IBKR_CLIENT_ID", "10"))
    
    print(f"Attempting to connect to TWS at {host}:{port} with CID {client_id}...")
    try:
        await asyncio.wait_for(ib.connectAsync(host, port, clientId=client_id, readonly=True), timeout=5)
        print("SUCCESS: Connected to TWS!")
        ib.disconnect()
    except asyncio.TimeoutError:
        print("FAILED: Connection timed out.")
    except Exception as e:
        print(f"FAILED: Connection error: {e}")

if __name__ == "__main__":
    asyncio.run(test_tws())
