# Interactive Brokers (IBKR) Integration

The AI Wall Street Engine supports fetching real-time market data (price and market capitalization) and historical bars via Interactive Brokers using two different providers:

1.  **`ibkr_proxy` (Recommended)**: Connects to a remote or local IBKR Proxy server. This is the most secure and flexible method.
2.  **`ibkr` (Legacy)**: Connects directly to a local TWS/Gateway instance.

---

## 1. IBKR Proxy Provider (Recommended)

The IBKR Proxy allows you to securely access market data from a central location (e.g., a home computer running TWS) from any other environment (e.g., GitHub Actions or a cloud server).

### Setup
Ensure the [IBKR Proxy](../apps/ibkr-proxy/README.md) is running and accessible via a public URL (e.g., Cloudflare Tunnel).

### Configuration
Set these in your `apps/engine/.env`:
```bash
FINANCIAL_PROVIDER=ibkr_proxy
IBKR_PROXY_URL=https://clvg.uk
IBKR_PROXY_TOKEN=your-secret-key
```

### GitHub Actions Setup

To use the Proxy in your automated pipeline:

1.  **Add Secrets**: Go to **Settings > Secrets and Variables > Actions** in your GitHub repository.
2.  **Add `IBKR_PROXY_URL`**: Set this to your proxy's public URL.
3.  **Add `IBKR_PROXY_TOKEN`**: Set this to your proxy's auth token.

The workflow at `.github/workflows/ingest.yml` is already configured to map these secrets to the environment.

---

## 2. Direct IBKR Provider (Legacy)

> [!WARNING]
> This method is for local use only and requires TWS/Gateway to be running on the same machine as the engine.

### Configuration
Set these in your `apps/engine/.env`:
```bash
FINANCIAL_PROVIDER=ibkr
IBKR_HOST=127.0.0.1
IBKR_PORT=7496
IBKR_CLIENT_ID=1
```

---

## Common IBKR Settings (All Providers)

Regardless of the provider, your Interactive Brokers TWS or Gateway must be configured correctly:

1.  **Enable API**: In TWS/Gateway, go to **Global Configuration > API > Settings**.
2.  **Socket Port**: Ensure it matches your `.env` (Default: `7496` for TWS, `4002` for Gateway).
3.  **Read-Only API**: Should be **checked** if you only need market data.
4.  **Allow connections from localhost only**: Usually **checked** for security (the Proxy handles the external routing).

## Troubleshooting

- **503 Service Unavailable (Proxy)**: The Proxy cannot reach TWS. Ensure TWS is logged in and the API is enabled on the Proxy's host.
- **Client ID already in use**: The Proxy automatically retries with random IDs. If using the legacy provider, ensure `IBKR_CLIENT_ID` is unique.
- **Connection Refused**: Check if the port matches and if TWS is actually running.

## High Availability & Multi-Provider Fallback

The engine is designed for maximum reliability. If the `ibkr_proxy` (or any primary provider) fails to deliver data due to network issues, rate limits, or proxy downtime, the `MarketDataManager` automatically falls back through a configured chain of providers.

By default, the system follows this hierarchy:
1.  **IBKR Proxy** (`ibkr_proxy`)
2.  **Financial Modeling Prep** (`fmp`)
3.  **Yahoo Finance** (`yfinance`)

Each provider is attempted **2 times** (configurable via `MARKET_DATA_RETRIES`) before moving to the next one in the chain. This multi-layered approach ensures that the daily pipeline can always complete its valuation and execution steps even if several market data sources are temporarily unavailable.
