# IBKR Integration (Legacy)

> [!WARNING]
> **This integration is LEGACY and no longer in active use.**
>
> The project now uses **Alpaca Paper Trading** as its third-party audit mirror for trade verification. All trades are fire-and-forget mirrored to Alpaca's paper API with agent-tagged metadata. See `docs/engine/trade-settlement-walkthrough.md` for details.
>
> IBKR remains available as a **market data provider** fallback (via `FINANCIAL_PROVIDER=ibkr_proxy` or `ibkr`), but it is no longer the primary broker integration for trade auditing.

---

## Historical Documentation

The following sections are preserved for reference but are not actively maintained.

### 1. IBKR Proxy Provider

The IBKR Proxy allows secure access to market data from a central location (e.g., a home computer running TWS) from any other environment.

**Configuration:**
```bash
FINANCIAL_PROVIDER=ibkr_proxy
IBKR_PROXY_URL=https://clvg.uk
IBKR_PROXY_TOKEN=your-secret-key
```

### 2. Direct IBKR Provider (Legacy)

Connects directly to a local TWS/Gateway instance. For local use only.

**Configuration:**
```bash
FINANCIAL_PROVIDER=ibkr
IBKR_HOST=127.0.0.1
IBKR_PORT=7496
IBKR_CLIENT_ID=1
```

### Common IBKR Settings

1. **Enable API**: In TWS/Gateway, go to **Global Configuration > API > Settings**.
2. **Socket Port**: Ensure it matches your `.env` (Default: `7496` for TWS, `4002` for Gateway).
3. **Read-Only API**: Should be **checked** if you only need market data.
4. **Allow connections from localhost only**: Usually **checked** for security.

### Troubleshooting

- **503 Service Unavailable (Proxy)**: The Proxy cannot reach TWS. Ensure TWS is logged in and the API is enabled on the Proxy's host.
- **Client ID already in use**: The Proxy automatically retries with random IDs. If using the legacy provider, ensure `IBKR_CLIENT_ID` is unique.
- **Connection Refused**: Check if the port matches and if TWS is actually running.

### High Availability

If the configured IBKR provider fails, `MarketDataManager` retries that provider and then falls back to the last known stored price in `price_history`. The engine also supports FMP and YFinance as alternative market data providers.