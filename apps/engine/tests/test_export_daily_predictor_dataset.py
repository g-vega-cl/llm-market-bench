import json
from unittest.mock import MagicMock

from scripts.export_daily_predictor_dataset import (
    build_assistant_response,
    build_user_message,
    export_predictor_dataset,
    format_sft_sample,
)


def test_build_user_message():
    msg = build_user_message("SPY", "Mock Context Text")
    assert "Asset: SPY" not in msg  # Context text provides asset
    assert "Market Context:\nMock Context Text" in msg
    assert "predict whether SPY will close HIGHER (UP) or LOWER (DOWN)" in msg


def test_build_assistant_response():
    row = {
        "predicted_direction": "UP",
        "confidence": 75.0,
        "expected_return_pct": 0.40,
        "rationale": "Strong pre-market gap fill.",
        "catalysts": ["PMI beat", "Yield easing"],
    }
    resp_str = build_assistant_response(row)
    data = json.loads(resp_str)
    assert data["predicted_direction"] == "UP"
    assert data["confidence"] == 75.0
    assert len(data["catalysts"]) == 2


def test_format_sft_sample():
    row = {
        "id": "pred-123",
        "target_date": "2026-09-23",
        "ticker": "SPY",
        "model_name": "deepseek-v4-flash",
        "prompt_variant_tag": "variant-test",
        "market_context": "Sample context details.",
        "predicted_direction": "DOWN",
        "confidence": 60.0,
        "expected_return_pct": -0.25,
        "rationale": "High yields and strong dollar.",
        "catalysts": ["UUP 8-week high"],
        "is_correct": True,
        "open_price": 774.0,
        "close_price": 773.0,
        "actual_direction": "DOWN",
        "brier_score": 0.16,
    }
    sample = format_sft_sample(row, prompt_content="System prompt test.")
    assert len(sample["messages"]) == 3
    assert sample["messages"][0]["role"] == "system"
    assert sample["messages"][0]["content"] == "System prompt test."
    assert sample["messages"][1]["role"] == "user"
    assert "Sample context details." in sample["messages"][1]["content"]
    assert sample["messages"][2]["role"] == "assistant"
    parsed_assistant = json.loads(sample["messages"][2]["content"])
    assert parsed_assistant["predicted_direction"] == "DOWN"
    assert sample["metadata"]["is_correct"] is True


def test_export_predictor_dataset_sft(tmp_path):
    mock_supabase = MagicMock()
    mock_rows = [
        {
            "id": "pred-1",
            "target_date": "2026-09-22",
            "ticker": "SPY",
            "model_name": "deepseek-v4-flash",
            "prompt_variant_tag": "tag-1",
            "market_context": "Market Context 1",
            "predicted_direction": "UP",
            "confidence": 70.0,
            "expected_return_pct": 0.35,
            "rationale": "Bullish momentum",
            "catalysts": ["Earnings beat"],
            "is_correct": True,
        },
        {
            "id": "pred-2",
            "target_date": "2026-09-23",
            "ticker": "SPY",
            "model_name": "MiniMax-M3",
            "prompt_variant_tag": "tag-2",
            "market_context": "Market Context 2",
            "predicted_direction": "DOWN",
            "confidence": 65.0,
            "expected_return_pct": -0.20,
            "rationale": "Hawkish Fed",
            "catalysts": ["Yield jump"],
            "is_correct": True,
        },
    ]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=mock_rows)

    mock_supabase.table.return_value.select.return_value.not_.is_.return_value = mock_query

    # Mock prompt experiments query
    mock_exp_query = MagicMock()
    mock_exp_query.execute.return_value = MagicMock(
        data=[{"variant_tag": "tag-1", "prompt_content": "System prompt 1"}]
    )
    mock_supabase.table.return_value.select.return_value.execute.side_effect = [
        mock_exp_query.execute.return_value,
    ]

    out_file = tmp_path / "test_sft.jsonl"
    count = export_predictor_dataset(
        supabase_client=mock_supabase,
        output_path=str(out_file),
        dataset_format="sft",
        only_correct=True,
    )

    assert count == 2
    assert out_file.exists()
    lines = out_file.read_text().strip().split("\n")
    assert len(lines) == 2
    first_record = json.loads(lines[0])
    assert first_record["messages"][0]["content"] == "System prompt 1"
    assert "Market Context 1" in first_record["messages"][1]["content"]


def test_export_predictor_dataset_dpo(tmp_path):
    mock_supabase = MagicMock()
    mock_rows = [
        {
            "id": "pred-1",
            "target_date": "2026-09-22",
            "ticker": "SPY",
            "model_name": "deepseek-v4-flash",
            "prompt_variant_tag": "tag-1",
            "market_context": "Market Context Shared",
            "predicted_direction": "DOWN",
            "confidence": 70.0,
            "expected_return_pct": -0.35,
            "rationale": "Correct bearish prediction",
            "catalysts": ["Fed hawkish"],
            "is_correct": True,
        },
        {
            "id": "pred-2",
            "target_date": "2026-09-22",
            "ticker": "SPY",
            "model_name": "MiniMax-M3",
            "prompt_variant_tag": "tag-1",
            "market_context": "Market Context Shared",
            "predicted_direction": "UP",
            "confidence": 65.0,
            "expected_return_pct": 0.20,
            "rationale": "Incorrect bullish prediction",
            "catalysts": ["Overbought rally"],
            "is_correct": False,
        },
    ]

    mock_query = MagicMock()
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.execute.return_value = MagicMock(data=mock_rows)

    mock_supabase.table.return_value.select.return_value.not_.is_.return_value = mock_query
    mock_supabase.table.return_value.select.return_value.execute.return_value = MagicMock(data=[])

    out_file = tmp_path / "test_dpo.jsonl"
    count = export_predictor_dataset(
        supabase_client=mock_supabase,
        output_path=str(out_file),
        dataset_format="dpo",
        only_correct=False,
    )

    assert count == 1
    assert out_file.exists()
    lines = out_file.read_text().strip().split("\n")
    assert len(lines) == 1
    dpo_record = json.loads(lines[0])
    assert "chosen" in dpo_record
    assert "rejected" in dpo_record
    assert json.loads(dpo_record["chosen"])["predicted_direction"] == "DOWN"
    assert json.loads(dpo_record["rejected"])["predicted_direction"] == "UP"
