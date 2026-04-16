# Correlation Matrix & Uncorrelated Asset Discovery

## Overview

The correlation matrix system identifies uncorrelated asset pairs with positive 90-day momentum for portfolio diversification. This enables AI Wall Street agents to discover diversification opportunities and supports the "XLK/XLE" (Technology + Energy) strategy concept that has gained popularity.

## Background: The Uncorrelated Assets Strategy

The strategy is simple but powerful:
1. Find two assets with **low correlation** (close to 0)
2. Both assets should have **positive long-term returns**
3. The combination reduces portfolio volatility without sacrificing returns

### Why This Works

- **Diversification:** When one asset falls, the other may not follow
- **Positive Drift:** Both assets contributing to long-term growth
- **Reduced Drawdowns:** Uncorrelated assets don't peak/trough together

## Ticker Universe

The system tracks **42 tickers** across multiple asset classes:

| Category | Tickers | Description |
|----------|---------|-------------|
| US Sectors | XLK, XLE, XLF, XLV, XLY, XLI, XLB, XLU, XLRE, XLC | 10 sector ETFs |
| US Broad | QQQ, VIG, IWM, SPY | Broad market & factor ETFs |
| Intl Dev | EFA, EWJ, EWG, EWL, EWP, SCZ, BWX | Developed markets |
| Emerging Markets | EEM, MCHI, EWZ, EIDO, EPI | EM broad & country ETFs |
| Commodities | GLD, SLV, PDBC, USO | Gold, silver, commodities |
| Bonds | TLT, IEF, LQD, EMB | Treasuries, investment grade |
| Intl Bonds | BNDX, IAGG | International aggregate bonds |
| Real Assets | VNQ, ICF | REITs |
| Dollar | UUP | Dollar index |
| Crypto | BTCUSD, ETHUSD | Bitcoin & Ethereum |
| Volatility | VIXY, VIXM | VIX short & mid-term futures |

## Methodology

### Rolling Window: 90 Days

- Industry standard (used by Barra, RiskMetrics)
- Long enough to filter noise
- Short enough to capture regime changes

### Correlation Methods

#### Pearson Correlation
- Standard linear correlation coefficient
- Measures strength of linear relationship
- Best for normally distributed returns
- Range: -1 (perfect negative) to +1 (perfect positive)

#### Spearman Correlation
- Rank-based (non-parametric)
- Measures monotonic relationship
- Robust to outliers and non-linear relationships
- Better for fat-tailed return distributions

### 90-Day Returns
- Total return from start to end of window
- Calculated as: `(P_end / P_start - 1) * 100`

## Pipeline

```
GitHub Actions (Sundays 16:00 ET)
         │
         ▼
correlation_matrix.py
         │
    ┌────┴────┐
    │         │
    ▼         ▼
FMP API    FMP API
(tickers)  (90d prices)
    │         │
    └────┬────┘
         ▼
Compute Returns
         │
         ▼
Pearson + Spearman
Correlation Matrices
         │
         ▼
Supabase Storage
         │
         ▼
/market-overview UI
```

## Database Schema

### Table: `correlation_runs`

Metadata for each weekly computation.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| run_date | DATE | Sunday of the run |
| created_at | TIMESTAMPTZ | UTC timestamp |
| window_days | INT | Rolling window (90) |
| num_assets | INT | Number of assets (42) |
| tickers | JSONB | Array of all tickers |

### Table: `correlation_data`

Full 42×42 matrix stored as pairs.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| run_id | UUID | FK → correlation_runs |
| ticker_a | TEXT | First asset |
| ticker_b | TEXT | Second asset |
| pearson_corr | FLOAT | Pearson correlation |
| spearman_corr | FLOAT | Spearman correlation |
| returns_a_90d | FLOAT | 90-day return for ticker_a (%) |
| returns_b_90d | FLOAT | 90-day return for ticker_b (%) |
| data_points | INT | Number of observations |

**Unique constraint:** `(run_id, ticker_a, ticker_b)` with `ticker_a < ticker_b` (alphabetical ordering)

## Agent Integration

### Tool: `find_uncorrelated_assets`

Agents can invoke this tool to find diversification opportunities:

```python
find_uncorrelated_assets(
    max_correlation: float = 0.3,  # Max absolute correlation
    min_return: float = 0.0,        # Min 90d return for both assets
    method: str = "pearson"         # "pearson" or "spearman"
)
```

**Example output:**
```
UNCORRELATED ASSET PAIRS (sorted by pearson correlation, lowest first):

1. XLE/BTCUSD:
   Pearson Correlation: 0.0007 | 90d Returns: 133.69% / 24.32%
2. EWZ/ETHUSD:
   Pearson Correlation: -0.0011 | 90d Returns: 17.32% / 0.79%
...
```

## Frontend: `/market-overview`

New public page accessible from nav with three main sections:

1. **How I'm Feeling Card** - Same sentiment analysis from Today page
2. **Correlation Heatmap** - Interactive 42×42 matrix with:
   - Pearson/Spearman toggle
   - Hover for exact values
   - Color gradient (blue=uncorrelated, red=highly correlated)
3. **Uncorrelated Pairs Table** - Filterable and sortable:
   - Max correlation slider
   - Min return slider
   - Method selection (Pearson/Spearman)
   - Sort by correlation or return

## Running Locally

```bash
cd apps/engine

# Activate virtual environment
source .venv/bin/activate

# Run correlation matrix computation
python correlation_matrix.py
```

## Adding New Tickers

1. Add ticker to `TICKER_UNIVERSE` list in `correlation_matrix.py`
2. Test with FMP: `python correlation_matrix.py` will verify ticker availability
3. If verification fails, ticker is automatically excluded

## Test Coverage

Tests are located in `apps/engine/tests/test_correlation_matrix.py`:

- **TestTickerUniverse** - Verifies ticker list completeness
- **TestComputeReturns** - Daily returns calculation
- **TestComputeCorrelationMatrices** - Pearson/Spearman computation
- **TestCompute90dReturns** - Total return calculation
- **TestTickerVerification** - FMP API verification logic
- **TestIntegration** - Full pipeline logic

Run tests:
```bash
cd apps/engine
source .venv/bin/activate
pytest tests/test_correlation_matrix.py -v
```

## Recent Results

Latest run (2026-04-16):
- **42 tickers** validated
- **861 pairs** computed
- **Most uncorrelated pairs:**
  - XLE/BTCUSD: 0.0007 (XLE +133.69%, BTC +24.32%)
  - EWZ/ETHUSD: -0.0011 (EWZ +17.32%, ETH +0.79%)

## Future Enhancements

- [ ] Backfill historical correlation data for regime analysis
- [ ] Add rolling correlation over time (correlation trend)
- [ ] Implement minimum spanning tree for portfolio construction
- [ ] Add factor exposure analysis (value, momentum, quality)
