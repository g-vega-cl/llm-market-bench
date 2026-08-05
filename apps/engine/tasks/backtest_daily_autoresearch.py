import argparse
import asyncio
import json
import os
import sqlite3
import sys
import uuid
from datetime import UTC, datetime, timedelta

# Inject path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from core.config import logger
from core.db import get_supabase_client
from core.llm.clients import close_client, get_deepseek_client
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_CONSTRAINTS_FOOTER,
    DAILY_PREDICTOR_CONSTRAINTS_HEADER,
    DAILY_PREDICTOR_PROMPT,
    DailyPredictionOutput,
    split_daily_predictor_prompt,
)
from tasks.daily_autoresearch import calculate_daily_ratchet_score

DB_PATH = ".backtest_daily.db"


def sync_to_supabase(table_name: str, record: dict):
    """Safely upsert record to Supabase if available."""
    try:
        client = get_supabase_client()
        client.table(table_name).upsert(record).execute()
    except Exception as e:
        logger.warning(f"Could not sync {table_name} to Supabase: {e}")


class DailyMetaPromptResponse(BaseModel):
    new_prompt: str


def init_backtest_daily_db():
    """Create local SQLite tables mirroring Supabase for sandboxed daily predictor backtests."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_predictions (
            id TEXT PRIMARY KEY,
            prediction_date TEXT,
            target_date TEXT,
            ticker TEXT,
            model_name TEXT,
            prompt_variant_tag TEXT,
            predicted_direction TEXT,
            confidence REAL,
            expected_return_pct REAL,
            rationale TEXT,
            catalysts TEXT,
            actual_open_price REAL,
            actual_close_price REAL,
            actual_direction TEXT,
            is_correct INTEGER,
            brier_score REAL,
            status TEXT,
            created_at TEXT,
            UNIQUE(target_date, ticker, model_name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prompt_experiments (
            id TEXT PRIMARY KEY,
            variant_tag TEXT UNIQUE,
            prompt_name TEXT,
            prompt_content TEXT,
            week_start TEXT,
            week_end TEXT,
            status TEXT,
            experiment_type TEXT,
            metrics TEXT,
            parent_tag TEXT,
            change_description TEXT,
            is_backtest INTEGER DEFAULT 1,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def reset_backtest_daily_db():
    """Clear all records from local backtest DB tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM daily_predictions")
    cursor.execute("DELETE FROM prompt_experiments")
    conn.commit()
    conn.close()


async def fetch_historical_spy_prices(target_date_str: str) -> tuple[float, float]:
    """Fetch or simulate historical Open and Close prices for SPY on target_date."""
    try:
        import yfinance as yf

        dt = datetime.strptime(target_date_str, "%Y-%m-%d")
        next_day = dt + timedelta(days=1)
        data = yf.download("SPY", start=dt.strftime("%Y-%m-%d"), end=next_day.strftime("%Y-%m-%d"), progress=False)

        if not data.empty and "Open" in data.columns and "Close" in data.columns:
            open_val = data["Open"].values.flat[0]
            close_val = data["Close"].values.flat[0]
            return float(open_val), float(close_val)
    except Exception as e:
        logger.warning(f"Could not fetch yfinance price for {target_date_str}: {e}. Using simulated prices.")

    # Synthetic fallback for deterministic testing/offline mode
    open_price = 500.0
    # Day-based deterministic fluctuation
    day_num = int(target_date_str.replace("-", "")) % 7
    close_price = open_price + (1.5 if day_num % 2 == 0 else -1.2)
    return open_price, close_price


async def get_active_backtest_daily_prompt() -> tuple[str, str]:
    """Fetch active prompt from local backtest DB or bootstrap baseline."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT variant_tag, prompt_content FROM prompt_experiments "
        "WHERE prompt_name = 'DAILY_PREDICTOR_PROMPT' AND status = 'active' "
        "ORDER BY created_at DESC LIMIT 1"
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return row["variant_tag"], row["prompt_content"]

    today_str = datetime.now(UTC).date().isoformat()
    tag = "daily-pred-backtest-base"

    exp_record = {
        "id": str(uuid.uuid4()),
        "variant_tag": tag,
        "prompt_name": "DAILY_PREDICTOR_PROMPT",
        "prompt_content": DAILY_PREDICTOR_PROMPT,
        "week_start": today_str,
        "week_end": today_str,
        "status": "active",
        "experiment_type": "baseline",
        "change_description": "Initial backtest baseline daily predictor prompt.",
        "is_backtest": True,
    }
    sync_to_supabase("prompt_experiments", exp_record)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO prompt_experiments (
            id, variant_tag, prompt_name, prompt_content, week_start, week_end,
            status, experiment_type, change_description, is_backtest, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'))
        """,
        (
            exp_record["id"],
            tag,
            "DAILY_PREDICTOR_PROMPT",
            DAILY_PREDICTOR_PROMPT,
            today_str,
            today_str,
            "active",
            "baseline",
            "Initial backtest baseline daily predictor prompt.",
        ),
    )
    conn.commit()
    conn.close()

    return tag, DAILY_PREDICTOR_PROMPT


async def run_simulated_daily_prediction(
    t_sim: datetime,
    active_prompt: str,
    prompt_tag: str,
    model_name: str = "deepseek-v4-flash",
    ticker: str = "SPY",
) -> dict | None:
    """Run daily prediction step at 09:00 AM ET for target_date using DeepSeek Flash."""
    target_date_str = t_sim.date().isoformat()
    deepseek_client = get_deepseek_client()

    context = (
        f"Asset: {ticker} (S&P 500 ETF)\n"
        f"Prediction Target Date: {target_date_str}\n"
        f"Simulated Timestamp: {t_sim.isoformat()}\n"
        f"Macro context: S&P 500 trading context prior to market open."
    )

    try:
        user_msg = (
            f"Market Context:\n{context}\n\n"
            f"Analyze market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
            f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
        )

        resp_awaitable = deepseek_client.chat.completions.create(
            model=model_name,
            response_model=DailyPredictionOutput,
            messages=[
                {"role": "system", "content": active_prompt},
                {"role": "user", "content": user_msg},
            ],
        )

        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        prediction_id = str(uuid.uuid4())
        catalysts_json = json.dumps(resp.catalysts or [])

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO daily_predictions (
                id, prediction_date, target_date, ticker, model_name, prompt_variant_tag,
                predicted_direction, confidence, expected_return_pct, rationale, catalysts,
                status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (
                prediction_id,
                target_date_str,
                target_date_str,
                ticker.upper(),
                model_name,
                prompt_tag,
                resp.predicted_direction.upper(),
                float(resp.confidence),
                float(resp.expected_return_pct),
                resp.rationale,
                catalysts_json,
                t_sim.isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        prediction_record = {
            "id": prediction_id,
            "prediction_date": target_date_str,
            "target_date": target_date_str,
            "ticker": ticker.upper(),
            "model_name": model_name,
            "prompt_variant_tag": prompt_tag,
            "predicted_direction": resp.predicted_direction.upper(),
            "confidence": float(resp.confidence),
            "expected_return_pct": float(resp.expected_return_pct),
            "rationale": resp.rationale,
            "catalysts": resp.catalysts or [],
            "status": "pending",
        }
        sync_to_supabase("daily_predictions", prediction_record)

        logger.info(
            f"[{t_sim.date()}] Simulated Daily Prediction ({model_name}): "
            f"{resp.predicted_direction} ({resp.confidence}% confidence)"
        )

        return {
            "id": prediction_id,
            "target_date": target_date_str,
            "ticker": ticker.upper(),
            "model_name": model_name,
            "predicted_direction": resp.predicted_direction.upper(),
            "confidence": float(resp.confidence),
        }
    except Exception as e:
        logger.error(f"Error running simulated daily prediction: {e}")
        return None
    finally:
        await close_client(deepseek_client, "deepseek")


async def evaluate_simulated_daily_prediction(
    t_sim: datetime,
    target_date: str,
    ticker: str = "SPY",
    open_price: float | None = None,
    close_price: float | None = None,
) -> dict | None:
    """Evaluate 05:15 PM ET daily prediction against actual market open/close prices."""
    if open_price is None or close_price is None:
        open_price, close_price = await fetch_historical_spy_prices(target_date)

    actual_direction = "UP" if close_price >= open_price else "DOWN"

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM daily_predictions WHERE target_date = ? AND ticker = ?",
        (target_date, ticker.upper()),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        logger.warning(f"No pending prediction found to evaluate for {target_date}")
        return None

    predicted_direction = row["predicted_direction"]
    confidence = row["confidence"] if row["confidence"] is not None else 50.0

    is_correct = 1 if predicted_direction == actual_direction else 0

    # Calculate Brier calibration score: (p - y)^2 where p = confidence/100.0, y = 1 if actual_direction == UP else 0
    # Or relative to predicted direction outcome:
    y_outcome = 1.0 if actual_direction == predicted_direction else 0.0
    p_prob = confidence / 100.0
    brier_score = float((p_prob - y_outcome) ** 2)

    cursor.execute(
        """
        UPDATE daily_predictions SET
            actual_open_price = ?,
            actual_close_price = ?,
            actual_direction = ?,
            is_correct = ?,
            brier_score = ?,
            status = 'evaluated'
        WHERE id = ?
        """,
        (open_price, close_price, actual_direction, is_correct, brier_score, row["id"]),
    )
    conn.commit()
    conn.close()

    eval_record = {
        "id": row["id"],
        "prediction_date": row["prediction_date"],
        "target_date": target_date,
        "ticker": ticker.upper(),
        "model_name": row["model_name"],
        "prompt_variant_tag": row["prompt_variant_tag"],
        "predicted_direction": predicted_direction,
        "confidence": confidence,
        "expected_return_pct": row["expected_return_pct"],
        "rationale": row["rationale"],
        "open_price": open_price,
        "close_price": close_price,
        "actual_direction": actual_direction,
        "is_correct": is_correct == 1,
        "brier_score": brier_score,
        "status": "evaluated",
    }
    sync_to_supabase("daily_predictions", eval_record)

    logger.info(
        f"[{target_date}] Evaluated Prediction: Predicted={predicted_direction}, Actual={actual_direction}, "
        f"Correct={is_correct == 1}, Brier={brier_score:.4f}"
    )

    return {
        "id": row["id"],
        "target_date": target_date,
        "is_correct": is_correct == 1,
        "actual_direction": actual_direction,
        "brier_score": brier_score,
    }


async def generate_new_daily_prompt_backtest(old_prompt: str, baseline_score: float) -> str:
    """Generate mutated strategy instruction prompt using DeepSeek Flash for backtest."""
    _, mutable_strategies, _ = split_daily_predictor_prompt(old_prompt)
    deepseek_client = get_deepseek_client()

    meta_prompt = (
        "You are a Meta-Researcher AI optimizing an LLM prompt for predicting intraday S&P 500 (SPY) open-to-close price movement.\n\n"
        f"The current prompt strategy achieved a ratchet score of {baseline_score:.2f}.\n"
        "Your goal is to rewrite ONLY the strategy / analytical reasoning section of the prompt "
        "to be more effective, focusing on macro catalyst extraction, technical level signals, momentum vs gap-fill behavior, "
        "and better confidence calibration.\n"
        "Do NOT include output formatting rules or JSON schema definitions; "
        "the required output structure is automatically enforced by the system.\n\n"
        "CURRENT STRATEGY INSTRUCTIONS:\n"
        f"```text\n{mutable_strategies}\n```\n\n"
        "Output ONLY the raw new strategy instructions text."
    )

    try:
        resp_awaitable = deepseek_client.chat.completions.create(
            model="deepseek-v4-flash",
            response_model=DailyMetaPromptResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable

        new_strategies = resp.new_prompt.strip()
        if new_strategies.startswith("```"):
            lines = new_strategies.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            new_strategies = "\n".join(lines).strip()

        return DAILY_PREDICTOR_CONSTRAINTS_HEADER + new_strategies + DAILY_PREDICTOR_CONSTRAINTS_FOOTER
    except Exception as e:
        logger.error(f"Error mutating backtest daily prompt: {e}")
        return old_prompt
    finally:
        await close_client(deepseek_client, "deepseek")


async def run_backtest_daily_autoresearch(start_date_str: str = "2026-04-27", weeks: int = 1) -> dict:
    """Run simulated S&P Daily Auto-Researcher backtest over N weeks using DeepSeek Flash."""
    init_backtest_daily_db()
    reset_backtest_daily_db()

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    logger.info(f"=== Starting S&P Daily Auto-Researcher Backtest ({start_date_str}, {weeks} week(s)) ===")
    logger.info("Using model: deepseek-v4-flash for both Daily Predictor and Meta-Researcher.")

    active_tag, active_prompt = await get_active_backtest_daily_prompt()

    evaluated_predictions = []
    current_ratchet_score = 0.0

    for week_idx in range(weeks):
        week_start = start_date + timedelta(weeks=week_idx)
        week_end = week_start + timedelta(days=5)

        logger.info(f"\n--- WEEK {week_idx + 1}/{weeks}: {week_start.date()} to {week_end.date()} ---")

        for day_offset in range(5):
            current_day = week_start + timedelta(days=day_offset)
            if current_day.weekday() >= 5:
                continue

            target_date_str = current_day.date().isoformat()

            # 1. Pre-Market Inference at 09:00 AM ET
            t_sim_am = current_day.replace(hour=9, minute=0, second=0)
            await run_simulated_daily_prediction(
                t_sim=t_sim_am,
                active_prompt=active_prompt,
                prompt_tag=active_tag,
                model_name="deepseek-v4-flash",
                ticker="SPY",
            )

            # 2. Post-Market Evaluation at 05:15 PM ET
            t_sim_pm = current_day.replace(hour=17, minute=15, second=0)
            eval_res = await evaluate_simulated_daily_prediction(
                t_sim=t_sim_pm,
                target_date=target_date_str,
                ticker="SPY",
            )
            if eval_res:
                evaluated_predictions.append(eval_res)

        # End of Week Ratchet Check & Meta-Researcher Mutation
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT is_correct, brier_score FROM daily_predictions WHERE status = 'evaluated'")
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()

        current_ratchet_score = calculate_daily_ratchet_score(rows)
        logger.info(
            f"End of Week {week_idx + 1} Ratchet Evaluation: "
            f"Score = {current_ratchet_score:.2f} (from {len(rows)} evaluated predictions)"
        )

        logger.info("Triggering DeepSeek Flash Meta-Researcher mutation...")
        new_prompt = await generate_new_daily_prompt_backtest(active_prompt, current_ratchet_score)

        new_tag = f"daily-pred-backtest-{uuid.uuid4().hex[:8]}"
        exp_id = str(uuid.uuid4())

        exp_record = {
            "id": exp_id,
            "variant_tag": new_tag,
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "prompt_content": new_prompt,
            "week_start": week_start.date().isoformat(),
            "week_end": week_end.date().isoformat(),
            "status": "active",
            "experiment_type": "incremental",
            "metrics": {"score": current_ratchet_score, "predictions": len(rows)},
            "parent_tag": active_tag,
            "change_description": f"Backtest mutation week {week_idx + 1} score {current_ratchet_score:.2f}",
            "is_backtest": True,
        }
        sync_to_supabase("prompt_experiments", exp_record)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO prompt_experiments (
                id, variant_tag, prompt_name, prompt_content, week_start, week_end,
                status, experiment_type, metrics, parent_tag, change_description, is_backtest, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', 'incremental', ?, ?, ?, 1, datetime('now'))
            """,
            (
                exp_id,
                new_tag,
                "DAILY_PREDICTOR_PROMPT",
                new_prompt,
                week_start.date().isoformat(),
                week_end.date().isoformat(),
                json.dumps({"score": current_ratchet_score, "predictions": len(rows)}),
                active_tag,
                f"Backtest mutation week {week_idx + 1} score {current_ratchet_score:.2f}",
            ),
        )
        conn.commit()
        conn.close()

        active_tag = new_tag
        active_prompt = new_prompt
        logger.info(f"Deployed new backtest prompt variant: {new_tag}")

    logger.info(f"=== S&P Daily Auto-Researcher Backtest Complete ({weeks} week(s)) ===")
    return {
        "weeks_completed": weeks,
        "predictions_evaluated": len(evaluated_predictions),
        "final_ratchet_score": current_ratchet_score,
        "final_prompt_variant": active_tag,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="S&P Daily Auto-Researcher Backtest CLI Runner")
    parser.add_argument("--start-date", default="2026-04-27", help="Backtest start date (YYYY-MM-DD)")
    parser.add_argument("--weeks", type=int, default=1, help="Number of simulated weeks")
    args = parser.parse_args()

    asyncio.run(run_backtest_daily_autoresearch(args.start_date, args.weeks))
