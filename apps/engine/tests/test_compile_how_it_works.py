from apps.engine.scripts.compile_how_it_works import parse_pipeline_markdown


def test_parse_pipeline_markdown():
    mock_md = """---
tags: [pipeline, test]
category: entity
---

# Pipeline Test

This is an introduction.

## Phase 1: Ingestion & Normalization
*   **Icon**: 📰
*   **Badge**: Tripled Trigger: Multiple Daily Runs
*   **Tags**: [FMP Cache, Gmail API, Trading Economics]

GitHub Actions fires the pipeline at market open, midday, and afternoon.
*   Scrapes unread emails from Gmail; removes ads via Gemini Flash
*   Economic Calendar ingestion from Trading Economics (bi-weekly)

## Phase 2: Pre-Analysis Setup
*   **Icon**: ⚙️
*   **Badge**: Market Hours Check
*   **Tags**: [FMP Cache, Global Macro Tracker]

Before LLM analysis, the engine prepares context.
*   Global Macro Snapshot: Real-time quotes
*   Portfolio Initialization: Fetches current prices
"""
    phases = parse_pipeline_markdown(mock_md)
    assert len(phases) == 2

    # Verify Phase 1
    p1 = phases[0]
    assert p1["phase"] == 1
    assert p1["title"] == "Ingestion & Normalization"
    assert p1["icon"] == "📰"
    assert p1["badge"] == "Tripled Trigger: Multiple Daily Runs"
    assert p1["tags"] == ["FMP Cache", "Gmail API", "Trading Economics"]
    assert p1["description"] == "GitHub Actions fires the pipeline at market open, midday, and afternoon."
    assert len(p1["bullets"]) == 2
    assert p1["bullets"][0] == "Scrapes unread emails from Gmail; removes ads via Gemini Flash"

    # Verify Phase 2
    p2 = phases[1]
    assert p2["phase"] == 2
    assert p2["title"] == "Pre-Analysis Setup"
    assert p2["icon"] == "⚙️"
    assert p2["badge"] == "Market Hours Check"
    assert p2["tags"] == ["FMP Cache", "Global Macro Tracker"]
    assert p2["description"] == "Before LLM analysis, the engine prepares context."
    assert len(p2["bullets"]) == 2
    assert p2["bullets"][1] == "Portfolio Initialization: Fetches current prices"
