"""Standalone dataset extractor for Laya training.

Reads evaluated market sessions from Supabase and formats them into
Laya's standard typed-decisions JSONL format (state, questions, gold).
Completely decoupled from apps/engine runtime.
"""

import argparse
import json
import os
from pathlib import Path

# Standard question contract matching Jev decisions model
DIRECTION_INSTRUCTIONS = (
    "Predict whether SPY will close HIGHER (UP) or LOWER (DOWN) at 4:00 PM ET "
    "compared to the 9:30 AM ET Open price."
)

DIRECTION_OPTIONS = {
    "UP": (
        "Close price >= Open price. Bullish intraday session: price holds above VWAP, "
        "positive overnight momentum continuation, falling bond yields, or strong bullish macro catalysts."
    ),
    "DOWN": (
        "Close price < Open price. Bearish intraday session: price rejects VWAP, "
        "gap-fill exhaustion, surging bond yields, high VIX, or negative macro catalysts."
    ),
}


def format_laya_record(
    context: str,
    target_date: str,
    actual_direction: str,
    ticker: str = "SPY",
) -> dict:
    """Format a single market session into Laya's typed-decisions schema."""
    direction = actual_direction.strip().upper()
    if direction not in ("UP", "DOWN"):
        raise ValueError(f"Invalid actual_direction: '{actual_direction}'. Must be 'UP' or 'DOWN'.")

    return {
        "state": context.strip(),
        "questions": {
            "direction": {
                "type": "choice",
                "instructions": DIRECTION_INSTRUCTIONS,
                "options": DIRECTION_OPTIONS,
            }
        },
        "gold": {
            "direction": {
                "choice": direction,
            }
        },
        "metadata": {
            "target_date": target_date,
            "ticker": ticker.upper(),
        },
    }


def reconstruct_context(prediction_row: dict, newsletter_map: dict[str, str]) -> str | None:
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

    # Sort strictly by target_date
    sorted_records = sorted(records, key=lambda r: r.get("metadata", {}).get("target_date", ""))

    split_idx = int(len(sorted_records) * (1.0 - val_ratio))
    # Ensure at least 1 item in val if len >= 2
    if split_idx >= len(sorted_records) and len(sorted_records) >= 2:
        split_idx = len(sorted_records) - 1

    train = sorted_records[:split_idx]
    val = sorted_records[split_idx:]
    return train, val


def get_supabase_client():
    """Create a standalone Supabase client using environment variables."""
    from dotenv import load_dotenv
    from supabase import create_client

    # Look for .env in apps/engine/.env or repo root
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

    print("Fetching evaluated daily predictions from Supabase...")
    resp = (
        client.table("daily_predictions")
        .select("id, target_date, ticker, actual_direction, market_context, status")
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
                # Prioritize 'open' (morning) newsletter if available
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

    # Build Laya records
    records = []
    skipped = 0
    for dt, row in date_to_pred.items():
        ctx = reconstruct_context(row, newsletter_map)
        if not ctx:
            skipped += 1
            continue

        record = format_laya_record(
            context=ctx,
            target_date=dt,
            actual_direction=row["actual_direction"],
            ticker=row.get("ticker", "SPY"),
        )
        records.append(record)

    print(f"Successfully constructed {len(records)} Laya records (skipped {skipped} due to missing context).")

    # Chronological split
    train_records, val_records = chronological_split(records, val_ratio=val_ratio)

    train_file = out_path / "train.jsonl"
    val_file = out_path / "val.jsonl"

    with open(train_file, "w") as f:
        for r in train_records:
            f.write(json.dumps(r) + "\n")

    with open(val_file, "w") as f:
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

        train_up = sum(1 for r in train_records if r["gold"]["direction"]["choice"] == "UP")
        val_up = sum(1 for r in val_records if r["gold"]["direction"]["choice"] == "UP")
        print(f"Class balance (Train): {train_up} UP / {len(train_records) - train_up} DOWN")
        print(f"Class balance (Val):   {val_up} UP / {len(val_records) - val_up} DOWN")

    return len(train_records), len(val_records)


def main():
    parser = argparse.ArgumentParser(description="Export daily predictor data to Laya typed-decisions JSONL.")
    parser.add_argument("--output-dir", default="data", help="Directory where train.jsonl and val.jsonl are saved.")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="Fraction of latest data reserved for validation.")
    args = parser.parse_args()

    export_dataset(output_dir=args.output_dir, val_ratio=args.val_ratio)


if __name__ == "__main__":
    main()
