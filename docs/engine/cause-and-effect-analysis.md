# Cause & Effect Analysis: Predicted vs Actual Impact

The Cause & Effect analysis is a bi-weekly pipeline (Tuesdays & Fridays) that audits past market events to track how accurately they were predicted and what their actual ripple effects were across specific sectors and companies.

## Technical Architecture

The following diagram maps the logical flow to specific functions and files in the codebase.

```mermaid
graph TD
    Start([Daily Pipeline]) -- "apps/engine/main.py" --> MainCall[perform_cause_and_effect_analysis]
    
    subgraph "analysis/cause_and_effect_analysis.py"
        MainCall --> GetEvents[Query 'memories' table via Supabase]
        GetEvents --> LoopEvents{For Each Event}
        
        LoopEvents --> ExactCheck{Check 'cause_and_effect' table for event_id}
        ExactCheck -- Skip --> EndLoop[Next Event]
        
        ExactCheck -- No --> SimilarCheck["find_similar_memory (memory/store.py)"]
        SimilarCheck -- Match Found --> AnalysisCheck{Check if match has record?}
        AnalysisCheck -- Yes --> EndLoop
        
        SimilarCheck -- No Match --> TickerStep["extract_related_tickers (local)"]
        AnalysisCheck -- No --> TickerStep
        
        TickerStep --> LLMTickers["Call Gemini (TickerSuggestion model)"]
        LLMTickers --> CombinedTickers[Merge with regex & benchmarks]
    end
    
    subgraph "External Modules"
        CombinedTickers -- "execution/market_data.py" --> FetchData["MarketDataManager.get_history()"]
    end
    
    subgraph "Final Step"
        FetchData --> FinalAnalysis["Analysis LLM (prompts.py templates)"]
        FinalAnalysis --> DBWrite["Insert into 'cause_and_effect' table"]
    end
    
    DBWrite --> EndLoop
    EndLoop --> End([Finished])
```

## Key Features

### 1. Semantic Deduplication
To prevent redundant analysis of similar narratives (e.g., repeating a "Fed Rate Hike" analysis twice), the engine uses pgvector similarity search.
- **Function**: `find_similar_memory` in `apps/engine/memory/store.py`.
- **Logic**: If an event has a similarity score > 0.90 with a previously analyzed memory within the last 7 days, it is skipped.

### 2. Dynamic Ticker Discovery
Instead of a hardcoded mapping, the engine dynamically identifies relevant stock tickers and sector ETFs for every event.
- **Function**: `extract_related_tickers` in `apps/engine/analysis/cause_and_effect_analysis.py`.
- **Model**: Uses Gemini Flash with the `TickerSuggestion` Pydantic model.
- **Capabilities**: Identifies direct mentions, sector proxies (e.g., XLF for banking), and derivative impacts (e.g., suppliers or competitors).

### 3. Historical Data Context
The engine pulls historical price data for all discovered tickers from the `MarketDataManager` to provide the LLM with concrete evidence of the event's impact.
- **Default Benchmarks**: `SPY` and `QQQ` are always included as baselines.

## How to Run
The Cause & Effect analysis is part of the main entry point:
```bash
python main.py
```
It only executes on the scheduled days (Tuesdays and Fridays) as defined in the `perform_cause_and_effect_analysis()` entry condition.

## Manual Verification
You can use the test suite to verify the deduplication and discovery logic:
```bash
pytest apps/engine/tests/test_cause_and_effect_dedupe.py
```
