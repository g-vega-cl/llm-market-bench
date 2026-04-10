# Global Macro Tracker (Market Regime Awareness)

The **Global Macro Tracker** is a specialized engine module designed to provide LLM agents with real-time "regime" awareness. By tracking key global indicators (yields, dollar index, commodities, and broad indices) and calculating their relative volatility, the engine helps agents distinguish between normal market noise and significant macro shifts.

## 1. Technical Overview

The tracker is implemented in `apps/engine/core/macro_tracker.py` and is executed as a pre-analysis step in the main pipeline. It identifies whether any major asset is moving beyond its historical 30-day standard deviation ($\sigma$).

### **Asset Selection**

The tracker monitors 16 high-liquidity assets that serve as proxies for global growth, inflation, and risk sentiment:

| Category | Assets | Rationale |
|---|---|---|
| **Equities** | `SPY`, `QQQ`, `DIA`, `IWM` | US Broad Market, Tech, Blue Chip, Small Cap |
| **International** | `EWJ`, `EWY`, `VGK`, `MCHI`, `EEM` | Japan, South Korea, Europe, China, Emerging Markets |
| **Commodities** | `GLD`, `SLV`, `CPER`, `USO` | Gold & Silver (Inflation/Safety), Copper (Growth), Oil |
| **Yields & Indices** | `IEF`, `UUP`, `VIXY` | 10-Yr Treasury (Rates), US Dollar (DXY), Volatility |

## 2. Volatility & Regime Detection

For each asset, the tracker fetches current quotes and up to 30 days of historical data. It then calculates the **daily percentage change** and compares it to the **30-day rolling standard deviation**.

### **Regime Classification**

| Signal | Threshold ($|change| / \sigma$) | System Flag |
|---|---|---|
| **Normal** | $\le 1.5\sigma$ | `Normal` |
| **Alert** | $> 1.5\sigma$ | `❗ UNUSUAL` |
| **Regime Shift** | $> 2.0\sigma$ | `⚠️ HIGHLY UNUSUAL (Regime Shift)` |

### **Example Output**

If the S&P 500 (`SPY`) moves $+2.5\%$ while its typical daily volatility is $1.0\%$, the tracker will flag it:
> `S&P 500 (SPY): 520.45 [+2.50% today] | ⚠️ HIGHLY UNUSUAL (Regime Shift) (30d stdev: 1.00%)`

## 3. Pipeline Integration

The macro context is injected directly into the LLM's user prompt during the parallel analysis phase (`apps/engine/analyze.py`).

### **Prompt Instruction** 🧠

Agents are explicitly instructed to interpret these numbers before generating trade signals:
> **Instruction:** Use this snapshot to understand if markets are risk-on, risk-off, or experiencing abnormal volatility. Do not bet against severe macro trends without an extraordinary catalyst.

This prevents the "Consensus Bias" where an LLM might chase a localized stock story while the broader macro environment is undergoing a severe liquidation event.

## 4. Usage & Configuration

The macro tracker is enabled by default in the `ingest` pipeline. To manually verify the output, you can run the `test_macro.py` utility:

```bash
python apps/engine/test_macro.py
```

### **Extending the Tracker**
To add new macro indicators (e.g., Bitcoin as a risk proxy), edit the `MACRO_TICKERS` dictionary in `apps/engine/core/macro_tracker.py`.
