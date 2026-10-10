"""Concurrent Jev System One Evaluator and Weekly Non-Chronological K-Fold Scorer."""

from __future__ import annotations

import asyncio
import os
import random
import sys
from typing import Any

import httpx

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apps.engine.local_autoresearch.manifest import (
    DataManifest,
    JevCriteriaConfig,
    format_jev_payload,
    pack_daily_context,
)

from core.config import JEV_MODEL, OPENROUTER_API_KEY

OPENROUTER_DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"


async def evaluate_single_day(
    day_record: dict[str, Any],
    criteria: JevCriteriaConfig,
    manifest: DataManifest,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
    model_name: str = JEV_MODEL,
) -> dict[str, Any]:
    """Execute intraday decision prediction for a single historical day using Jev on OpenRouter."""
    context = pack_daily_context(day_record, manifest)
    ticker = day_record.get("ticker", "SPY")
    actual_dir = str(day_record.get("actual_direction", "UP")).upper()

    key = api_key or OPENROUTER_API_KEY
    if not key:
        raise ValueError("OPENROUTER_API_KEY is not set. Cannot run Jev prediction.")

    payload = format_jev_payload(context, criteria, ticker=ticker, model_name=model_name)
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }

    should_close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        should_close_client = True

    try:
        resp = await client.post(OPENROUTER_DECISIONS_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise RuntimeError(f"OpenRouter Decisions API error {resp.status_code}: {resp.text}")
        data = resp.json()
    finally:
        if should_close_client:
            await client.aclose()

    answers = data.get("answers", {})
    dir_ans = answers.get("direction", {})
    choice = str(dir_ans.get("choice", "UP")).upper()
    probabilities = dir_ans.get("probabilities", {})
    prob = float(probabilities.get(choice, dir_ans.get("confidence", 0.5)))
    confidence = round(prob * 100.0, 1) if prob <= 1.0 else round(prob, 1)

    # Determine if trade passes confidence gate
    is_gated_out = confidence < criteria.min_confidence
    gated_action = "NO_TRADE" if is_gated_out else choice

    is_correct = choice == actual_dir
    prob_actual = float(probabilities.get(actual_dir, 1.0 - prob if is_correct else prob))
    brier_score = round(float((1.0 - prob_actual) ** 2), 4)

    open_p = float(day_record.get("open_price", 0.0))
    close_p = float(day_record.get("close_price", 0.0))
    high_p = float(day_record.get("high_price", max(open_p, close_p)))
    low_p = float(day_record.get("low_price", min(open_p, close_p)))

    intraday_hit = (high_p > open_p) if choice == "UP" else (low_p < open_p)

    return {
        "target_date": day_record.get("target_date"),
        "predicted_direction": choice,
        "gated_action": gated_action,
        "actual_direction": actual_dir,
        "open_price": open_p,
        "close_price": close_p,
        "high_price": high_p,
        "low_price": low_p,
        "expected_return_pct": 0.0,
        "confidence": confidence,
        "probabilities": probabilities,
        "is_correct": is_correct,
        "intraday_hit": intraday_hit,
        "is_traded": not is_gated_out,
        "brier_score": brier_score,
    }


async def evaluate_batch(
    days: list[dict[str, Any]],
    criteria: JevCriteriaConfig,
    manifest: DataManifest,
    max_concurrency: int = 10,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Evaluate a batch of days concurrently using an asyncio semaphore."""
    sem = asyncio.Semaphore(max_concurrency)
    should_close = False
    if client is None:
        client = httpx.AsyncClient(timeout=45.0)
        should_close = True

    async def _eval(d: dict[str, Any]) -> dict[str, Any]:
        async with sem:
            return await evaluate_single_day(
                d,
                criteria=criteria,
                manifest=manifest,
                client=client,
                api_key=api_key,
            )

    try:
        tasks = [_eval(d) for d in days]
        return await asyncio.gather(*tasks)
    finally:
        if should_close:
            await client.aclose()


def calculate_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate ratchet evaluation metrics from evaluation results using canonical formula."""
    from tasks.daily_autoresearch import calculate_daily_ratchet_metrics

    if not results:
        return {
            "total_days": 0,
            "traded_days": 0,
            "close_accuracy_pct": 0.0,
            "intraday_hit_pct": 0.0,
            "magnitude_capture_pct": 0.0,
            "traded_win_rate_pct": 0.0,
            "mean_brier": 0.25,
            "score": 0.0,
        }

    canonical = calculate_daily_ratchet_metrics(results)
    total_days = len(results)
    traded_results = [r for r in results if r.get("is_traded", True)]
    traded_days = len(traded_results)

    traded_acc = (sum(1 for r in traded_results if r["is_correct"]) / traded_days * 100.0) if traded_days > 0 else 50.0

    selectivity_pct = round((traded_days / total_days) * 100.0, 2)

    return {
        "total_days": total_days,
        "traded_days": traded_days,
        "selectivity_pct": selectivity_pct,
        "traded_win_rate_pct": round(traded_acc, 2),
        "close_accuracy_pct": canonical["close_accuracy_pct"],
        "intraday_hit_pct": canonical["intraday_hit_pct"],
        "magnitude_capture_pct": canonical["magnitude_capture_pct"],
        "mean_brier": canonical["mean_brier"],
        "score": canonical["score"],
    }


async def evaluate_weekly_kfold(
    weekly_data: dict[str, list[dict[str, Any]]],
    criteria: JevCriteriaConfig,
    manifest: DataManifest,
    train_ratio: float = 0.75,
    seed: int = 42,
    max_concurrency: int = 10,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Execute non-chronological weekly block cross-validation.

    Guarantees:
    - Never splits calendar weeks across train and test.
    - Shuffles week blocks randomly so training doesn't overfit to recent regimes.
    - Applies explicit Overfit Penalty when train score exceeds test score.
    """
    week_keys = sorted(weekly_data.keys())
    if not week_keys:
        empty_m = calculate_metrics([])
        return {
            "train_metrics": empty_m,
            "test_metrics": empty_m,
            "overfit_penalty": 0.0,
            "effective_score": 0.0,
            "train_weeks": [],
            "test_weeks": [],
        }

    # Deterministic pseudo-random shuffle of week keys
    rng = random.Random(seed)
    shuffled_weeks = list(week_keys)
    rng.shuffle(shuffled_weeks)

    split_idx = max(1, int(len(shuffled_weeks) * train_ratio))
    train_weeks = set(shuffled_weeks[:split_idx])
    test_weeks = set(shuffled_weeks[split_idx:]) or set(shuffled_weeks[:1])

    train_days: list[dict[str, Any]] = []
    for w in sorted(train_weeks):
        train_days.extend(weekly_data[w])

    test_days: list[dict[str, Any]] = []
    for w in sorted(test_weeks):
        test_days.extend(weekly_data[w])

    # Evaluate train and test sets
    train_res = await evaluate_batch(
        train_days,
        criteria=criteria,
        manifest=manifest,
        max_concurrency=max_concurrency,
        client=client,
        api_key=api_key,
    )
    test_res = await evaluate_batch(
        test_days,
        criteria=criteria,
        manifest=manifest,
        max_concurrency=max_concurrency,
        client=client,
        api_key=api_key,
    )

    train_metrics = calculate_metrics(train_res)
    test_metrics = calculate_metrics(test_res)

    overfit_penalty = max(0.0, train_metrics["score"] - test_metrics["score"])
    effective_score = test_metrics["score"] - (0.5 * overfit_penalty)

    # Per-week metrics breakdown
    res_by_date = {r["target_date"]: r for r in train_res + test_res if r.get("target_date")}
    weekly_breakdown = {}
    for w in sorted(week_keys):
        w_days = weekly_data[w]
        w_res = [res_by_date[d["target_date"]] for d in w_days if d.get("target_date") in res_by_date]
        w_metrics = calculate_metrics(w_res)
        weekly_breakdown[w] = {
            "split": "TRAIN" if w in train_weeks else "TEST",
            "days_count": len(w_res),
            "score": w_metrics["score"],
            "accuracy_pct": w_metrics["close_accuracy_pct"],
            "traded_win_rate_pct": w_metrics["traded_win_rate_pct"],
            "traded_days": w_metrics["traded_days"],
        }

    return {
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "overfit_penalty": round(overfit_penalty, 2),
        "effective_score": round(effective_score, 2),
        "train_weeks": sorted(train_weeks),
        "test_weeks": sorted(test_weeks),
        "weekly_breakdown": weekly_breakdown,
    }


def split_weekly_vault(
    weekly_data: dict[str, list[dict[str, Any]]],
    vault_ratio: float = 0.20,
    seed: int = 42,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    """Deterministically partition historical weeks into an Active Optimization Pool and a Locked Vault.

    The Locked Vault is completely hidden from the meta-researcher's feedback loop
    to prevent multiple hypothesis testing and backtest overfitting.
    """
    week_keys = sorted(weekly_data.keys())
    if len(week_keys) < 4:
        return weekly_data, {}

    rng = random.Random(seed)
    shuffled = list(week_keys)
    rng.shuffle(shuffled)

    vault_count = max(1, int(len(shuffled) * vault_ratio))
    vault_keys = set(shuffled[:vault_count])
    active_keys = set(shuffled[vault_count:])

    active_pool = {k: weekly_data[k] for k in sorted(active_keys)}
    vault_pool = {k: weekly_data[k] for k in sorted(vault_keys)}
    return active_pool, vault_pool


async def evaluate_vault(
    vault_data: dict[str, list[dict[str, Any]]],
    criteria: JevCriteriaConfig,
    manifest: DataManifest,
    max_concurrency: int = 10,
    client: httpx.AsyncClient | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Evaluate candidate prompt and manifest strictly on the Locked Vault weeks."""
    vault_days: list[dict[str, Any]] = []
    for days in vault_data.values():
        vault_days.extend(days)

    if not vault_days:
        return calculate_metrics([])

    results = await evaluate_batch(
        vault_days,
        criteria=criteria,
        manifest=manifest,
        max_concurrency=max_concurrency,
        client=client,
        api_key=api_key,
    )
    return calculate_metrics(results)
