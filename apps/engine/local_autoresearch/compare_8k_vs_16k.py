"""Empirical Head-to-Head Comparison: 8k vs 16k Max Tokens on Non-Continuous Sessions.

Evaluates Strata ORCA with unconstrained reasoning (reasoning_budget_tokens: -1) across
20 strictly non-continuous, pre-market ground-truth trading sessions.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import time
from typing import Any

import httpx

# Add engine to path
sys.path.insert(0, os.path.abspath("apps/engine"))

from core.llm.daily_predictor_prompts import DAILY_PREDICTOR_PROMPT
from local_autoresearch.single_prompt_ratchet import (
    calculate_balanced_accuracy,
    evaluate_prediction_record,
    extract_daily_prediction,
    format_single_prompt_user_message,
)

DEFAULT_STRATA_URL = os.getenv("STRATA_BASE_URL", "http://127.0.0.1:8080/v1")
DEFAULT_STRATA_MODEL = os.getenv("STRATA_MODEL", "orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs")
RESULTS_FILE = ".compare_8k_vs_16k_results.json"


def select_non_continuous_sessions(
    db_path: str = ".live_production_sessions.db", count: int = 20
) -> list[dict[str, Any]]:
    """Select count strictly non-continuous sessions spanning the dataset."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM live_sessions ORDER BY target_date ASC").fetchall()
    all_sessions = [dict(r) for r in rows]
    conn.close()

    if len(all_sessions) < count:
        raise ValueError(f"Need at least {count} sessions, found {len(all_sessions)}")

    indices = [int(i * (len(all_sessions) - 1) / (count - 1)) for i in range(count)]
    for j in range(1, len(indices)):
        if indices[j] <= indices[j - 1]:
            indices[j] = indices[j - 1] + 2
        elif indices[j] == indices[j - 1] + 1:
            indices[j] += 1

    if indices[-1] >= len(all_sessions):
        for k in range(len(indices) - 1, 0, -1):
            if indices[k] >= len(all_sessions):
                indices[k] = len(all_sessions) - 1 - (len(indices) - 1 - k) * 2

    return [all_sessions[idx] for idx in indices]


async def query_strata_stream(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int,
    base_url: str = DEFAULT_STRATA_URL,
    model: str = DEFAULT_STRATA_MODEL,
    timeout: float = 400.0,
) -> tuple[str, float, int]:
    """Query Strata with streaming to track exact thinking tokens and avoid read timeouts."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": max_tokens,
        "reasoning_budget_tokens": -1,
        "stream": True,
    }

    t0 = time.time()
    thinking_chunks = 0
    full_content: list[str] = []

    async with client.stream("POST", url, json=payload, timeout=timeout) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break
            try:
                chunk = json.loads(data_str)
                delta = chunk["choices"][0]["delta"]
                if "reasoning_content" in delta and delta["reasoning_content"]:
                    thinking_chunks += 1
                if "content" in delta and delta["content"]:
                    full_content.append(delta["content"])
            except Exception:
                pass

    elapsed = time.time() - t0
    raw_content = "".join(full_content)
    return raw_content, elapsed, thinking_chunks


async def run_head_to_head_comparison():
    sessions = select_non_continuous_sessions(count=20)
    print("=" * 80)
    print(f"STARTING HEAD-TO-HEAD COMPARISON: 8k vs 16k on {len(sessions)} Non-Continuous Sessions")
    print("=" * 80)

    # Resume from existing results if partially done
    results_history: list[dict[str, Any]] = []
    completed_dates: set[str] = set()
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE) as f:
                saved = json.load(f)
                results_history = saved.get("sessions", [])
                completed_dates = {s["target_date"] for s in results_history}
                print(f"Loaded {len(results_history)} previously completed comparisons from {RESULTS_FILE}.")
        except Exception:
            pass

    records_8k: list[dict[str, Any]] = [s["run_8k"] for s in results_history]
    records_16k: list[dict[str, Any]] = [s["run_16k"] for s in results_history]

    async with httpx.AsyncClient(timeout=600.0) as client:
        for idx, session in enumerate(sessions):
            target_date = session["target_date"]
            if target_date in completed_dates:
                continue

            actual_dir = session["actual_direction"]
            user_msg = format_single_prompt_user_message(session)

            print(f"\n--- [{idx + 1:02d}/{len(sessions):02d}] {target_date} (Ground Truth: {actual_dir}) ---")

            # 1. Run 8k
            print("  Running 8k (budget ~6,144 tokens)...", end="", flush=True)
            raw_8k, dt_8k, think_8k = await query_strata_stream(
                client=client,
                system_prompt=DAILY_PREDICTOR_PROMPT,
                user_prompt=user_msg,
                max_tokens=8192,
                timeout=360.0,
            )
            pred_8k = extract_daily_prediction(raw_8k)
            rec_8k = evaluate_prediction_record(session, pred_8k)
            rec_8k["elapsed_sec"] = round(dt_8k, 1)
            rec_8k["thinking_chunks"] = think_8k
            status_8k = "HIT" if rec_8k["is_correct"] else "MISS"
            print(
                f" Done in {dt_8k:.1f}s | Pred: {rec_8k['predicted_direction']} ({rec_8k['confidence']:.0f}%) [{status_8k}]"
            )

            # 2. Run 16k
            print("  Running 16k (budget ~12,288 tokens)...", end="", flush=True)
            raw_16k, dt_16k, think_16k = await query_strata_stream(
                client=client,
                system_prompt=DAILY_PREDICTOR_PROMPT,
                user_prompt=user_msg,
                max_tokens=16384,
                timeout=550.0,
            )
            pred_16k = extract_daily_prediction(raw_16k)
            rec_16k = evaluate_prediction_record(session, pred_16k)
            rec_16k["elapsed_sec"] = round(dt_16k, 1)
            rec_16k["thinking_chunks"] = think_16k
            status_16k = "HIT" if rec_16k["is_correct"] else "MISS"
            print(
                f" Done in {dt_16k:.1f}s | Pred: {rec_16k['predicted_direction']} ({rec_16k['confidence']:.0f}%) [{status_16k}]"
            )

            # Summary comparison
            agree = rec_8k["predicted_direction"] == rec_16k["predicted_direction"]
            agree_str = "AGREE" if agree else "DIVERGE ⚠️"
            print(f"  Result: 8k={status_8k} | 16k={status_16k} | {agree_str}")

            records_8k.append(rec_8k)
            records_16k.append(rec_16k)

            comparison_entry = {
                "target_date": target_date,
                "actual_direction": actual_dir,
                "open_price": session["open_price"],
                "close_price": session["close_price"],
                "run_8k": rec_8k,
                "run_16k": rec_16k,
                "agree": agree,
            }
            results_history.append(comparison_entry)

            # Save state
            bal_8k = calculate_balanced_accuracy(records_8k)
            bal_16k = calculate_balanced_accuracy(records_16k)
            state_data = {
                "completed_sessions": len(results_history),
                "total_target": len(sessions),
                "summary_8k": {
                    "win_rate_pct": bal_8k["win_rate_pct"],
                    "balanced_accuracy_pct": bal_8k["balanced_accuracy_pct"],
                    "mcc": bal_8k["mcc"],
                    "avg_latency_sec": round(sum(r["elapsed_sec"] for r in records_8k) / len(records_8k), 1),
                },
                "summary_16k": {
                    "win_rate_pct": bal_16k["win_rate_pct"],
                    "balanced_accuracy_pct": bal_16k["balanced_accuracy_pct"],
                    "mcc": bal_16k["mcc"],
                    "avg_latency_sec": round(sum(r["elapsed_sec"] for r in records_16k) / len(records_16k), 1),
                },
                "agreement_pct": round(sum(1 for s in results_history if s["agree"]) / len(results_history) * 100.0, 1),
                "sessions": results_history,
            }
            with open(RESULTS_FILE, "w") as f:
                json.dump(state_data, f, indent=2)

    # Final summary report
    print("\n" + "=" * 80)
    print("FINAL HEAD-TO-HEAD BENCHMARK SUMMARY (20 Non-Continuous Sessions)")
    print("=" * 80)
    print(
        f"8k Max Tokens:  Win Rate: {bal_8k['win_rate_pct']:.1f}% | Balanced Acc: {bal_8k['balanced_accuracy_pct']:.1f}% | MCC: {bal_8k['mcc']:.3f} | Avg Latency: {state_data['summary_8k']['avg_latency_sec']}s"
    )
    print(
        f"16k Max Tokens: Win Rate: {bal_16k['win_rate_pct']:.1f}% | Balanced Acc: {bal_16k['balanced_accuracy_pct']:.1f}% | MCC: {bal_16k['mcc']:.3f} | Avg Latency: {state_data['summary_16k']['avg_latency_sec']}s"
    )
    print(f"Directional Agreement: {state_data['agreement_pct']:.1f}%")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_head_to_head_comparison())
