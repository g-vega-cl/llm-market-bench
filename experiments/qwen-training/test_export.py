from export_dataset import (
    build_assistant_outcome,
    build_user_prompt,
    chronological_split,
    format_qwen_sample,
    reconstruct_context,
)


def test_build_assistant_outcome():
    row = {
        "actual_direction": "UP",
        "open_price": 750.0,
        "close_price": 756.0,
    }
    outcome = build_assistant_outcome(row)
    assert outcome["predicted_direction"] == "UP"
    assert outcome["expected_return_pct"] == 0.8
    assert "confidence" not in outcome
    assert "rationale" not in outcome


def test_build_assistant_outcome_down():
    row = {
        "actual_direction": "DOWN",
        "open_price": 760.0,
        "close_price": 752.4,
    }
    outcome = build_assistant_outcome(row)
    assert outcome["predicted_direction"] == "DOWN"
    assert outcome["expected_return_pct"] == -1.0
    assert "confidence" not in outcome
    assert "rationale" not in outcome


def test_build_user_prompt():
    prompt = build_user_prompt("SPY", "Morning Newsletter Content")
    assert "Asset: SPY (S&P 500 ETF)" in prompt
    assert "Morning Newsletter Content" in prompt
    assert "predict whether SPY will close HIGHER (UP) or LOWER (DOWN)" in prompt


def test_format_qwen_sample():
    row = {
        "target_date": "2026-09-25",
        "ticker": "SPY",
        "actual_direction": "UP",
        "open_price": 750.0,
        "close_price": 755.0,
        "market_context": "Sample macro context",
    }
    sample = format_qwen_sample(row, "Sample macro context")
    assert "messages" in sample
    assert len(sample["messages"]) == 3
    assert sample["messages"][0]["role"] == "system"
    assert sample["messages"][1]["role"] == "user"
    assert sample["messages"][2]["role"] == "assistant"
    assert sample["metadata"]["target_date"] == "2026-09-25"
    assert sample["metadata"]["actual_direction"] == "UP"


def test_reconstruct_context():
    row_with_ctx = {"market_context": "Existing context"}
    assert reconstruct_context(row_with_ctx, {}) == "Existing context"

    row_without_ctx = {"target_date": "2026-05-15", "market_context": None}
    newsletter_map = {"2026-05-15": "Newsletter text for May 15"}
    assert (
        reconstruct_context(row_without_ctx, newsletter_map)
        == "Morning Newsletter Briefing (2026-05-15):\nNewsletter text for May 15"
    )

    row_missing = {"target_date": "2026-01-01", "market_context": None}
    assert reconstruct_context(row_missing, {}) is None


def test_chronological_split():
    records = [{"metadata": {"target_date": f"2026-05-0{i}"}} for i in range(1, 6)]
    train, val = chronological_split(records, val_ratio=0.2)
    assert len(train) == 4
    assert len(val) == 1
    assert val[0]["metadata"]["target_date"] == "2026-05-05"
