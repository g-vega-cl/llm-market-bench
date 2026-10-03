"""Standalone dataset extractor for Qwen 3.8 27B SFT fine-tuning.

Extracts historical market sessions from Supabase and pairs the morning
pre-market context (newsletters, macro indicators, overnight gaps) directly
with the true market close outcome (actual direction and return percentage).

Completely decoupled from apps/engine runtime.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any

QWEN_SYSTEM_PROMPT = """You are an elite quantitative macro trader analyzing intraday S&P 500 (SPY) price action.
Your goal is to predict whether today's 4:00 PM ET Close price will be higher (UP) or lower (DOWN) than today's 9:30 AM ET Open price.

=== REQUIRED OUTPUT FORMAT ===
You MUST return a valid JSON object (enclosed in { and }) containing:
{
  "predicted_direction": "UP" or "DOWN",
  "expected_return_pct": <float estimated percentage return from Open to Close, e.g. +0.45 or -0.30>
}
Do not output raw Markdown headers, bullet lists, or YAML."""


def build_user_prompt(ticker: str, context: str) -> str:
    """Format the exact user prompt matching the production daily predictor."""
    return (
        f"Market Context:\nAsset: {ticker} (S&P 500 ETF)\n{context}\n\n"
        f"Analyze the market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
        f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
    )


def build_assistant_outcome(row: dict[str, Any]) -> dict[str, Any]:
    """Format the ground truth market outcome into direction and return percentage."""
    actual_direction = str(row.get("actual_direction", "UP")).upper()
    open_p = float(row.get("open_price") or 0.0)
    close_p = float(row.get("close_price") or 0.0)

    if open_p > 0 and close_p > 0:
        return_pct = round(((close_p - open_p) / open_p) * 100.0, 2)
    else:
        return_pct = 0.0

    return {
        "predicted_direction": actual_direction,
        "expected_return_pct": return_pct,
    }


def format_qwen_sample(row: dict[str, Any], context: str) -> dict[str, Any]:
    """Format a single session into OpenAI / ChatML standard message format."""
    ticker = str(row.get("ticker", "SPY")).upper()
    user_prompt = build_user_prompt(ticker, context)
    outcome = build_assistant_outcome(row)
    assistant_content = json.dumps(outcome)

    open_p = float(row.get("open_price") or 0.0)
    close_p = float(row.get("close_price") or 0.0)
    return_pct = round(((close_p - open_p) / open_p) * 100.0, 2) if open_p > 0 and close_p > 0 else 0.0

    return {
        "messages": [
            {"role": "system", "content": QWEN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_content},
        ],
        "metadata": {
            "target_date": row.get("target_date"),
            "ticker": ticker,
            "actual_direction": row.get("actual_direction"),
            "open_price": open_p,
            "close_price": close_p,
            "actual_return_pct": return_pct,
        },
    }


def reconstruct_context(prediction_row: dict[str, Any], newsletter_map: dict[str, str]) -> str | None:
    """Extract context from row or fallback to synthesized newsletter for date."""
    ctx = prediction_row.get("market_context")
    if ctx and str(ctx).strip():
        return str(ctx).strip()

    target_date = prediction_row.get("target_date")
    if target_date and target_date in newsletter_map:
        nl_content = newsletter_map[target_date]
        if nl_content and str(nl_content).strip():
            return f"Morning Newsletter Briefing ({target_date}):\n{str(nl_content).strip()}"

    return None


def chronological_split(records: list[dict], val_ratio: float = 0.2) -> tuple[list[dict], list[dict]]:
    """Sort records chronologically by target_date and split into train and val."""
    if not records:
        return [], []

    sorted_records = sorted(records, key=lambda r: r.get("metadata", {}).get("target_date", ""))
    split_idx = int(len(sorted_records) * (1.0 - val_ratio))
    if split_idx >= len(sorted_records) and len(sorted_records) >= 2:
        split_idx = len(sorted_records) - 1

    return sorted_records[:split_idx], sorted_records[split_idx:]


def get_supabase_client():
    """Create a standalone Supabase client using environment variables."""
    from dotenv import load_dotenv
    from supabase import create_client

    repo_root = Path(__file__).resolve().parent.parent.parent
    engine_env = repo_root / "apps" / "engine" / ".env"
    root_env = repo_root / ".env"

    if engine_env.exists():
        load_dotenv(engine_env)
    elif root_env.exists():
        load_dotenv(root_env)
    else:
        load_dotenv()

    url = os.getenv("SUPABASE_PROJECT_URL") or os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

    if not url or not key:
        raise ValueError("Missing SUPABASE_PROJECT_URL or SUPABASE_SERVICE_ROLE_KEY in environment.")

    return create_client(url, key)


def export_dataset(output_dir: str = "data", val_ratio: float = 0.2) -> tuple[int, int]:
    """Extract, process, and write train.jsonl and val.jsonl."""
    client = get_supabase_client()
    out_path = Path(__file__).resolve().parent / output_dir
    out_path.mkdir(parents=True, exist_ok=True)

    print("Fetching evaluated daily predictions with actual outcomes from Supabase...")
    resp = (
        client.table("daily_predictions")
        .select("id, target_date, ticker, actual_direction, open_price, close_price, market_context, status")
        .eq("status", "evaluated")
        .order("target_date", desc=False)
        .execute()
    )
    raw_preds = resp.data or []
    print(f"Retrieved {len(raw_preds)} evaluated prediction records.")

    # Deduplicate predictions by target_date (keeping one per date)
    date_to_pred: dict[str, dict] = {}
    for row in raw_preds:
        d = row.get("target_date")
        actual_dir = row.get("actual_direction")
        if d and actual_dir in ("UP", "DOWN") and d not in date_to_pred:
            date_to_pred[d] = row

    print(f"Unique evaluated trading dates: {len(date_to_pred)}")

    # Fetch newsletters for dates needing fallback context
    dates_needing_newsletter = [d for d, r in date_to_pred.items() if not r.get("market_context")]
    print(f"Dates requiring newsletter fallback: {len(dates_needing_newsletter)}")

    newsletter_map: dict[str, str] = {}
    if dates_needing_newsletter:
        nl_resp = client.table("generated_newsletters").select("created_at, content, session").execute()
        for nl in nl_resp.data or []:
            raw_dt = str(nl.get("created_at") or "")
            dt = raw_dt[:10]
            content = nl.get("content")
            session = nl.get("session")
            if dt and content:
                if dt not in newsletter_map or session == "open":
                    newsletter_map[dt] = content
        print(f"Loaded {len(newsletter_map)} generated newsletters.")

        missing_dates = [d for d in dates_needing_newsletter if d not in newsletter_map]
        if missing_dates:
            print(f"Checking newsletter_snapshots for {len(missing_dates)} remaining dates...")
            snap_resp = client.table("newsletter_snapshots").select("date, subject, content").execute()
            for snap in snap_resp.data or []:
                raw_dt = str(snap.get("date") or "")
                dt = raw_dt[:10]
                content = snap.get("content")
                subj = snap.get("subject") or "Market Update"
                if dt in missing_dates and content and dt not in newsletter_map:
                    newsletter_map[dt] = f"Subject: {subj}\n\n{content}"
            print(f"Total newsletters available after snapshot fallback: {len(newsletter_map)}")

    # Build Qwen records
    records = []
    skipped = 0
    for dt, row in date_to_pred.items():
        ctx = reconstruct_context(row, newsletter_map)
        if not ctx:
            skipped += 1
            continue

        record = format_qwen_sample(row, ctx)
        records.append(record)

    print(f"Successfully constructed {len(records)} Qwen training records (skipped {skipped} due to missing context).")

    # Chronological split
    train_records, val_records = chronological_split(records, val_ratio=val_ratio)

    train_file = out_path / "train.jsonl"
    val_file = out_path / "val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for r in train_records:
            f.write(json.dumps(r) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for r in val_records:
            f.write(json.dumps(r) + "\n")

    print(f"Wrote {len(train_records)} training records to {train_file}")
    print(f"Wrote {len(val_records)} validation records to {val_file}")

    if train_records and val_records:
        train_start = train_records[0]["metadata"]["target_date"]
        train_end = train_records[-1]["metadata"]["target_date"]
        val_start = val_records[0]["metadata"]["target_date"]
        val_end = val_records[-1]["metadata"]["target_date"]
        print(f"Train date span: {train_start} -> {train_end}")
        print(f"Val date span:   {val_start} -> {val_end}")

        train_up = sum(1 for r in train_records if r["metadata"]["actual_direction"] == "UP")
        val_up = sum(1 for r in val_records if r["metadata"]["actual_direction"] == "UP")
        print(f"Class balance (Train): {train_up} UP / {len(train_records) - train_up} DOWN")
        print(f"Class balance (Val):   {val_up} UP / {len(val_records) - val_up} DOWN")

    return len(train_records), len(val_records)


def main():
    parser = argparse.ArgumentParser(description="Export daily predictor data to Qwen SFT JSONL.")
    parser.add_argument("--output-dir", default="data", help="Directory where train.jsonl and val.jsonl are saved.")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Fraction of latest data reserved for validation.")
    args = parser.parse_args()

    export_dataset(output_dir=args.output_dir, val_ratio=args.val_ratio)


if __name__ == "__main__":
    main()
