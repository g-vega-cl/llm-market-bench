# Asset Discovery: Thematic Pipeline

The **Asset Discovery Pipeline** is a specialized engine that identifies actionable investment assets (stocks, ETFs) driven by specific market catalysts or macro events. 

Unlike generic screening, this pipeline uses a **three-stage AI-driven process** to ensure that identified assets are not only sectorally relevant but also logically aligned with the event's "How to Profit" thesis.

---

## 1. Discovery Architecture

The pipeline consists of three distinct phases: **Mapping**, **Retrieval**, and **Re-Ranking**.

### **Phase 1: Thematic Mapping (Gemini)**
- **Objective**: Translate a complex market event (e.g., "Suez Canal Blockage") into specific financial search parameters.
- **Provider**: `GEMINI_MODEL` (Gemini 2.x/3.x Flash)
- **Output**: `DiscoveryThemes` object containing:
    - Target **Sectors** and **Industries**.
    - Search **Keywords** for business description matching.
    - `market_cap_min`: A dynamic floor to filter out "uncrowded" or "niche" plays.

### **Phase 2: Expanded Candidate Retrieval (FMP)**
- **Objective**: Fetch a broad pool of candidates using the mapping parameters.
- **Provider**: **Financial Modeling Prep (FMP)** `screen_stocks` endpoint.
- **Logic**: 
    - Executes multiple screening calls based on mapped sectors and industries.
    - Applies the dynamic `market_cap_min` filter (typically $2B+ default, but can be lower for niche themes).
    - Collects up to **50+ candidates** per theme.

### **Phase 3: Thematic Re-Ranking (DeepSeek)**
- **Objective**: Perform high-reasoning evaluation of the candidate pool against the specific event thesis.
- **Provider**: `DEEPSEEK_MODEL` (DeepSeek-Reasoner) using **Thinking Mode**.
- **Logic**: 
    - Evaluates each asset's business model against the "Bottleneck" or "Primary Beneficiary" logic of the event.
    - **Relevance Score (0-100)**: Assigns a score based on conviction.
    - **How to Profit Reasoning**: Explains *why* this specific asset is expected to move (e.g., "Direct exposure to localized supply chain disruptions").
    - **Filtering**: Assets with a score `< 40` are automatically excluded from the final analysis.

---

## 2. Technical Data Models

The discovery engine uses structured Pydantic models to ensure predictable data flow:

### **`RankedAsset`**
```python
class RankedAsset(BaseModel):
    ticker: str
    name: str
    relevance_score: int  # 0-100
    how_to_profit: str    # Why this ticker is relevant to the theme
    sector: str
    industry: str
```

### **`DiscoveryRankingResponse`**
```python
class DiscoveryRankingResponse(BaseModel):
    ranked_assets: List[RankedAsset]
```

### **`DiscoveryThemes`**
```python
class DiscoveryThemes(BaseModel):
    sectors: List[str]
    industries: List[str]
    keywords: List[str]
    market_cap_min: float  # In USD (e.g. 2000000000.0)
```

---

## 3. Why This Approach?

#### **Precision vs. Recall**
Generic screeners have high recall (they find all tech stocks) but low precision (most aren't relevant to a specific AI chip shortage). By using **DeepSeek re-ranking**, we filter out the "noise" and provide the Parallel LLM Analysis engine with high-conviction targets.

#### **Low-Latency Synthesis**
While we fetch 50+ candidates, only the **Top 15-20** highest-ranked assets are passed to the 4 parallel LLMs. This keeps token usage efficient and focuses the "skeptical verifiers" on the most plausible trades.

#### **Dynamic Market Cap Filtering**
The engine can now automatically pivot between "Blue Chip" safety and "Small Cap" opportunity based on the event's scale, removing the hardcoded $1B+ floor that previously limited discovery.

---

## 4. Operational Flow

1. **`DiscoveryService.discover_assets(event)`**: Entry point.
2. **`_map_event_to_themes(event)`**: Gemini pass.
3. **`_fetch_candidates(themes)`**: FMP screening pass.
4. **`_rank_candidates_with_llm(candidates, event)`**: DeepSeek re-ranking pass.
5. **Output**: List of `RankedAsset` objects.

---

## 5. Verification
The discovery pipeline quality is verified using:
- **`pytest apps/engine/tests/test_discovery_quality.py`**: Validates the end-to-end multi-stage flow and scoring logic.
