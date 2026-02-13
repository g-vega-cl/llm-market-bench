# Interactive Brokers (IBKR) Integration

The AI Wall Street Engine supports fetching real-time market data (price and market capitalization) and historical bars directly from Interactive Brokers via a local Gateway or TWS instance.

## Prerequisites

1.  **IBKR Gateway or TWS**: You must have the IBKR Gateway or Trader Workstation (TWS) running on your local machine or a reachable server.
2.  **API Settings**:
    *   Enable "ActiveX and Socket Clients".
    *   Set the "Socket Port" (Default: `7496` for TWS, `4002` for Gateway).
    *   (Optional but recommended) Uncheck "Read-Only API" if you intend to perform trades later, though the current integration is read-only.
3.  **Dependencies**: The engine requires the `ib-async` library.

## Configuration

Set the following environment variables in your `.env` file:

```bash
FINANCIAL_PROVIDER=ibkr
IBKR_HOST=127.0.0.1
IBKR_PORT=7496
IBKR_CLIENT_ID=1
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `FINANCIAL_PROVIDER` | Set to `ibkr` to use this provider. | `yfinance` |
| `IBKR_HOST` | The IP address where IBKR is running. | `127.0.0.1` |
| `IBKR_PORT` | The socket port configured in IBKR. | `7496` |
| `IBKR_CLIENT_ID` | A unique ID for the connection. | `1` |

## How it Works

### Real-time Quotes
The provider uses the `ib-async` `reqTickersAsync` method to fetch current market prices. This is high-speed and efficient for local data.

### Market Capitalization
IBKR does not provide market cap via standard ticks. The engine fetches a `ReportSnapshot` from IBKR's fundamental data service, parses the XML, and extracts the `MKTCAP` ratio.

### Connection Safety
The connection is established with `readonly=True` to prevent accidental synchronization of orders or executions, ensuring the engine remains in a "read" state for market data fetching. Low-level `ib_async` internal logs are suppressed to keep the terminal output clean.

## Troubleshooting

- **Connection Refused**: Ensure the Gateway/TWS is open and the port matches your `.env`.
- **Read-Only Warnings**: If you see `Warning 321`, it means your IBKR instance has "Read-Only API" checked in its global configuration. This is fine for data fetching.
- **Missing Market Cap**: Fundamental data may not be available for all tickers (e.g., some international stocks or small caps).
