"""Export daily predictor predictions and market context into training datasets (SFT & DPO).

Extracts historical predictions with their full market context from Supabase and formats
them into JSONL datasets ready for Supervised Fine-Tuning (SFT) or Direct Preference Optimization (DPO).
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import get_supabase_client
from core.llm.daily_predictor_prompts import DAILY_PREDICTOR_PROMPT

logger = logging.getLogger("export_dataset")


def build_user_message(ticker: str, context: str) -> str:
    """Reconstructs the exact user prompt passed to the predictor model."""
    return (
        f"Market Context:\n{context}\n\n"
        f"Analyze the market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
        f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
    )


def build_assistant_response(row: dict[str, Any]) -> str:
    """Formats model prediction output as standard JSON matching DailyPredictionOutput."""
    output = {
        "predicted_direction": row.get("predicted_direction"),
        "confidence": row.get("confidence"),
        "expected_return_pct": row.get("expected_return_pct"),
        "rationale": row.get("rationale"),
        "catalysts": row.get("catalysts") or [],
    }
    return json.dumps(output)


def format_sft_sample(row: dict[str, Any], prompt_content: str | None = None) -> dict[str, Any]:
    """Formats a single prediction record into OpenAI/Chat standard SFT message format."""
    system_prompt = prompt_content or DAILY_PREDICTOR_PROMPT
    user_prompt = build_user_message(row.get("ticker", "SPY"), row.get("market_context", ""))
    assistant_resp = build_assistant_response(row)

    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_resp},
        ],
        "metadata": {
            "prediction_id": row.get("id"),
            "target_date": row.get("target_date"),
            "ticker": row.get("ticker"),
            "model_name": row.get("model_name"),
            "prompt_variant_tag": row.get("prompt_variant_tag"),
            "is_correct": row.get("is_correct"),
            "open_price": row.get("open_price"),
            "close_price": row.get("close_price"),
            "actual_direction": row.get("actual_direction"),
            "brier_score": row.get("brier_score"),
            "postmortem_category": row.get("postmortem_category"),
            "postmortem_flawed_assumption": row.get("postmortem_flawed_assumption"),
            "postmortem_lesson": row.get("postmortem_lesson"),
            "was_predictable": row.get("was_predictable"),
        },
    }


def export_predictor_dataset(
    supabase_client: Any = None,
    output_path: str = "daily_predictor_train.jsonl",
    dataset_format: str = "sft",
    only_correct: bool = True,
    model_filter: str | None = None,
    min_confidence: float = 50.0,
) -> int:
    """Exports daily predictor dataset from Supabase to a JSONL file.

    Args:
        supabase_client: Optional Supabase client instance.
        output_path: Destination JSONL file path.
        dataset_format: Format to output ('sft' or 'dpo').
        only_correct: If True (default for SFT), export only winning predictions.
        model_filter: Optional filter by model_name.
        min_confidence: Minimum prediction confidence filter.

    Returns:
        Number of samples exported.
    """
    if supabase_client is None:
        supabase_client = get_supabase_client()

    query = supabase_client.table("daily_predictions").select("*").not_.is_("market_context", "null")

    if only_correct:
        query = query.eq("is_correct", True)

    if model_filter:
        query = query.eq("model_name", model_filter)

    if min_confidence > 50.0:
        query = query.gte("confidence", min_confidence)

    query = query.order("target_date", desc=False)
    res = query.execute()
    rows = res.data or []

    if not rows:
        logger.warning("No prediction records found with market_context matching specified criteria.")
        return 0

    # Fetch prompt variants map if available
    exp_res = supabase_client.table("prompt_experiments").select("variant_tag, prompt_content").execute()
    prompt_map = {e["variant_tag"]: e["prompt_content"] for e in (exp_res.data or []) if e.get("variant_tag")}

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(out_file, "w", encoding="utf-8") as f:
        if dataset_format == "sft":
            for r in rows:
                tag = r.get("prompt_variant_tag")
                prompt_text = prompt_map.get(tag, DAILY_PREDICTOR_PROMPT)
                sample = format_sft_sample(r, prompt_content=prompt_text)
                f.write(json.dumps(sample) + "\n")
                count += 1

        elif dataset_format == "dpo":
            # Group predictions by (target_date, ticker) to form preference pairs
            grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
            for r in rows:
                key = (str(r.get("target_date")), str(r.get("ticker")))
                grouped.setdefault(key, []).append(r)

            for (target_date, ticker), group in grouped.items():
                correct = [p for p in group if p.get("is_correct") is True]
                incorrect = [p for p in group if p.get("is_correct") is False]

                if correct and incorrect:
                    chosen = correct[0]
                    rejected = incorrect[0]

                    context_text = chosen.get("market_context") or rejected.get("market_context") or ""
                    user_prompt = build_user_message(ticker, context_text)
                    system_prompt = prompt_map.get(chosen.get("prompt_variant_tag"), DAILY_PREDICTOR_PROMPT)

                    dpo_sample = {
                        "system": system_prompt,
                        "prompt": user_prompt,
                        "chosen": build_assistant_response(chosen),
                        "rejected": build_assistant_response(rejected),
                        "target_date": target_date,
                        "ticker": ticker,
                        "chosen_model": chosen.get("model_name"),
                        "rejected_model": rejected.get("model_name"),
                        "rejected_postmortem_category": rejected.get("postmortem_category"),
                        "rejected_postmortem_lesson": rejected.get("postmortem_lesson"),
                    }
                    f.write(json.dumps(dpo_sample) + "\n")
                    count += 1

    logger.info("Successfully exported %d %s samples to %s", count, dataset_format.upper(), output_path)
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="Export daily predictor training dataset from Supabase.")
    parser.add_argument("--output", type=str, default="data/daily_predictor_train.jsonl", help="Output JSONL path")
    parser.add_argument("--format", type=str, choices=["sft", "dpo"], default="sft", help="Dataset format (sft or dpo)")
    parser.add_argument(
        "--all", action="store_true", help="Include all predictions (default for SFT is only winning predictions)"
    )
    parser.add_argument("--model", type=str, default=None, help="Filter by model_name (e.g. deepseek-v4-flash)")
    parser.add_argument(
        "--min-confidence", type=float, default=50.0, help="Minimum confidence threshold (default: 50.0)"
    )

    args = parser.parse_args()
    export_predictor_dataset(
        output_path=args.output,
        dataset_format=args.format,
        only_correct=not args.all,
        model_filter=args.model,
        min_confidence=args.min_confidence,
    )
