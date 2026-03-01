# IBKR Proxy

This is a secure API proxy for Interactive Brokers (IBKR). It exposes an authenticated endpoint via Cloudflare Tunnel, allowing you to fetch market data from your local TWS/Gateway from anywhere.

## Setup

1.  **IBKR TWS/Gateway Configuration:**
    - Go to **API > Settings**.
    - Enable **"ActiveX and Socket Clients"**.
    - Set Socket Port to **7496** (TWS) or **7497** (Paper).
    - Ensure **"Read-Only API"** is checked.

2.  **Environment Setup:**
    - Create a `.env` file in this directory:
    ```env
    IBKR_PROXY_API_KEY=your-secret-password
    IBKR_HOST=127.0.0.1
    IBKR_PORT=7496
    ```

3.  **Run the Proxy:**
    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

4.  **Cloudflare Tunnel:**
    - Map a Public Hostname (e.g., `clvg.uk`) to `http://localhost:8000` in the Cloudflare Zero Trust dashboard.

## Usage

All endpoints require an `Authorization: Bearer <key>` header.

- **Get Price:** `GET /price/{ticker}`
- **Get History:** `GET /history/{ticker}?days=n`
- **Health Check:** `GET /`

### 📖 Interactive API Docs
Once the server is running, you can access the interactive documentation at:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Example Test
```bash
curl -H "Authorization: Bearer your-secret-password" https://clvg.uk/price/AAPL
```

## Troubleshooting
If you see a `503 Service Unavailable` or `TimeoutError`:
- Ensure TWS is logged in and the API is enabled.
- The proxy automatically retries with random Client IDs to avoid "ClientId already in use" errors.
