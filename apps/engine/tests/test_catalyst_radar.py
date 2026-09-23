"""Tests for Catalyst Radar core logic, date offsets, digestion stages, and concept-calendar matching."""

from datetime import date

from analysis.catalyst_radar import (
    CatalystRadarItem,
    calculate_date_offset,
    compute_and_store_catalyst_radar,
    fetch_catalyst_radar,
    format_catalyst_radar_context,
    match_concepts_to_catalysts,
)


def test_calculate_date_offset_stages():
    """Verify exact relative date strings and 4-stage lifecycle."""
    ref_date = date(2026, 9, 9)

    # 1. Upcoming tests
    delta, stage, label = calculate_date_offset("2026-09-16", ref_date)
    assert delta == 7
    assert stage == "upcoming"
    assert label == "1 week from now"

    delta, stage, label = calculate_date_offset("2026-09-23", ref_date)
    assert delta == 14
    assert stage == "upcoming"
    assert label == "2 weeks from now"

    delta, stage, label = calculate_date_offset("2026-09-12", ref_date)
    assert delta == 3
    assert stage == "upcoming"
    assert label == "in 3 days"

    delta, stage, label = calculate_date_offset("2026-09-10", ref_date)
    assert delta == 1
    assert stage == "upcoming"
    assert label == "tomorrow"

    # 2. Active / Today
    delta, stage, label = calculate_date_offset("2026-09-09", ref_date)
    assert delta == 0
    assert stage == "active"
    assert label == "today"

    # 3. Digesting (1 to 3 days ago)
    delta, stage, label = calculate_date_offset("2026-09-08", ref_date)
    assert delta == -1
    assert stage == "digesting"
    assert label == "digesting, 1 day ago"

    delta, stage, label = calculate_date_offset("2026-09-06", ref_date)
    assert delta == -3
    assert stage == "digesting"
    assert label == "digesting, 3 days ago"

    # 4. Expired (> 3 days ago)
    delta, stage, label = calculate_date_offset("2026-09-05", ref_date)
    assert delta == -4
    assert stage == "expired"
    assert label == "expired"


def test_clean_catalyst_title_prefix_stripping():
    """Verify that strategy/category prefixes (GEOPOLITICAL:, INFLATION:, etc.) are cleanly stripped."""
    from analysis.catalyst_radar import clean_catalyst_title

    raw1 = "[CALENDAR EVENT] (N/A) 2026-09-24: GEOPOLITICAL: US President Trump and President Xi Summit | Impact: HIGH | Date: 2026-09-24"
    assert clean_catalyst_title(raw1) == "US President Trump and President Xi Summit"

    raw2 = "[CALENDAR EVENT] (02:00 PM) 2026-09-25: INFLATION: US Michigan 5 Year Inflation: Long-term inflation expectation | Impact: NEUTRAL"
    assert clean_catalyst_title(raw2) == "US Michigan 5 Year Inflation"

    raw3 = "[CALENDAR EVENT] (01:00 PM) 2026-09-23: South Africa Interest Rate Decision (CENTRAL_BANK): Central bank decision"
    assert clean_catalyst_title(raw3) == "South Africa Interest Rate Decision"

    raw4 = "[CALENDAR EVENT] (08:30 AM) 2026-09-24: EMPLOYMENT: US Initial Jobless Claims: Weekly claims report"
    assert clean_catalyst_title(raw4) == "US Initial Jobless Claims"

    raw5 = "[CALENDAR EVENT] (12:30 PM) 2026-09-29: GDP: Canada GDP MoM JUL: Monthly GDP"
    assert clean_catalyst_title(raw5) == "Canada GDP MoM JUL"


def test_match_concepts_to_catalysts():
    """Verify vector similarity matching, velocity thresholding, and digestion inclusion."""
    ref_date = date(2026, 9, 9)

    # Concept A: High velocity (3.2), Vector [1.0, 0.0, 0.0]
    # Concept B: Low velocity (0.8), Vector [0.0, 1.0, 0.0] (should be filtered out by min_velocity=1.2)
    concepts = [
        {
            "id": "c1",
            "concept_name": "Semiconductor Export Controls",
            "velocity_score": 3.2,
            "mention_count": 5,
            "concept_vector": [1.0, 0.0, 0.0],
        },
        {
            "id": "c2",
            "concept_name": "Regional Banking Strains",
            "velocity_score": 0.8,
            "mention_count": 2,
            "concept_vector": [0.0, 1.0, 0.0],
        },
    ]

    # Memory 1: Matching Concept A, target date 2026-09-16 (1 week from now)
    # Memory 2: Expired memory from 2026-09-01 (should be excluded)
    calendar_memories = [
        {
            "id": "m1",
            "content": "[CALENDAR EVENT] (8:00 AM) TSMC Monthly Revenue Report",
            "target_date": "2026-09-16",
            "importance_score": 8,
            "embedding": [0.95, 0.05, 0.0],
            "metadata": {"impact": "BULLISH", "ticker": "TSM"},
        },
        {
            "id": "m2",
            "content": "[CALENDAR EVENT] Outdated July GDP print",
            "target_date": "2026-09-01",
            "importance_score": 8,
            "embedding": [0.95, 0.05, 0.0],
            "metadata": {},
        },
    ]

    results = match_concepts_to_catalysts(
        concepts=concepts,
        calendar_memories=calendar_memories,
        ref_date=ref_date,
        min_velocity=1.2,
        min_similarity=0.35,
        days_ahead=14,
        include_digesting=True,
    )

    assert len(results) == 1
    item = results[0]
    assert item.concept_name == "Semiconductor Export Controls"
    assert item.velocity_score == 3.2
    assert "TSMC Monthly Revenue Report" in item.catalyst_title
    assert item.target_date == "2026-09-16"
    assert item.date_offset_label == "1 week from now"
    assert item.stage == "upcoming"
    assert item.days_to_event == 7
    assert item.similarity >= 0.9


def test_format_catalyst_radar_context_lean_vs_detail():
    """Verify lean markdown table output for detail=False vs extended excerpts for detail=True."""
    item = CatalystRadarItem(
        concept_id="c1",
        concept_name="AI Datacenter Power Demand",
        velocity_score=2.8,
        catalyst_id="m1",
        catalyst_title="US Utilities & Energy Grid Earnings",
        target_date="2026-09-11",
        days_to_event=2,
        stage="upcoming",
        date_offset_label="in 2 days",
        impact="HIGH VOLATILITY",
        similarity=0.82,
        memory_content="Full memory text discussing energy grid capex...",
        related_tickers=["CEG", "VST"],
    )

    # Lean output
    lean_text = format_catalyst_radar_context([item], detail=False)
    assert "| Concept | Velocity | Catalyst Event | Target Date | Status | Impact |" in lean_text
    assert "AI Datacenter Power Demand" in lean_text
    assert "in 2 days" in lean_text
    assert "Full memory text" not in lean_text

    # Detailed output
    detail_text = format_catalyst_radar_context([item], detail=True)
    assert "Full memory text discussing energy grid capex..." in detail_text
    assert "- **Related Tickers**: CEG, VST" in detail_text


def test_compute_and_store_catalyst_radar(monkeypatch):
    """Verify compute_and_store_catalyst_radar extracts vectors and persists to catalyst_radar."""
    upserted_records = []

    class MockQuery:
        def __init__(self, data=None):
            self.data = data or []

        def select(self, *args, **kwargs):
            return self

        def gte(self, *args, **kwargs):
            return self

        def order(self, *args, **kwargs):
            return self

        def eq(self, *args, **kwargs):
            return self

        @property
        def not_(self):
            class MockNot:
                def __init__(self, parent):
                    self.parent = parent

                def is_(self, *args, **kwargs):
                    return self.parent

            return MockNot(self)

        def delete(self):
            return self

        def lt(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def upsert(self, records, on_conflict=None):
            upserted_records.extend(records)
            return self

        def execute(self):
            return self

    class MockSB:
        def table(self, name):
            if name == "concept_metrics":
                return MockQuery(
                    [
                        {
                            "id": "c1",
                            "concept_name": "AI Power",
                            "velocity_score": 3.0,
                            "concept_vector": [1.0, 0.0],
                        }
                    ]
                )
            if name == "memories":
                return MockQuery(
                    [
                        {
                            "id": "m1",
                            "content": "[CALENDAR EVENT] Grid Capex",
                            "target_date": "2026-09-12",
                            "importance_score": 8,
                            "embedding": [1.0, 0.0],
                            "metadata": {"impact": "BULLISH"},
                        }
                    ]
                )
            return MockQuery([])

    mock_sb = MockSB()
    ref_date = date(2026, 9, 9)
    count = compute_and_store_catalyst_radar(sb_client=mock_sb, ref_date=ref_date)

    assert count == 1
    assert len(upserted_records) == 1
    assert upserted_records[0]["concept_name"] == "AI Power"
    assert upserted_records[0]["catalyst_title"] == "Grid Capex"


def test_fetch_catalyst_radar_from_table():
    """Verify fetch_catalyst_radar reads pre-computed table rows and computes dates on read."""

    class MockQuery:
        def __init__(self, data=None):
            self.data = data or []

        def select(self, *args, **kwargs):
            return self

        def gte(self, *args, **kwargs):
            return self

        def order(self, *args, **kwargs):
            return self

        def limit(self, *args, **kwargs):
            return self

        def execute(self):
            return self

    class MockSB:
        def table(self, name):
            if name == "catalyst_radar":
                return MockQuery(
                    [
                        {
                            "concept_id": "c1",
                            "concept_name": "Cloud AI",
                            "velocity_score": 4.5,
                            "catalyst_id": "m1",
                            "catalyst_title": "Nvidia GTC",
                            "target_date": "2026-09-10",
                            "impact": "BULLISH",
                            "similarity": 0.88,
                            "memory_content": "GTC Keynote",
                            "related_tickers": ["NVDA"],
                        }
                    ]
                )
            return MockQuery([])

    mock_sb = MockSB()
    ref_date = date(2026, 9, 9)
    items = fetch_catalyst_radar(sb_client=mock_sb, ref_date=ref_date)

    assert len(items) == 1
    assert items[0].concept_name == "Cloud AI"
    assert items[0].days_to_event == 1
    assert items[0].date_offset_label == "tomorrow"
    assert items[0].stage == "upcoming"
