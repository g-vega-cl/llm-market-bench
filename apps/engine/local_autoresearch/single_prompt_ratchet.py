"""Single-Prompt Ground-Truth Ratchet for Local Autoresearch.

Evaluates and optimizes DAILY_PREDICTOR_PROMPT directly against real materialized
production sessions using local Strata (Qwen 32B), Stage 1 screening sieve, and
exact binomial statistical significance testing.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
from typing import Any

import httpx
from scipy.stats import binomtest

# Ensure apps/engine root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.llm.daily_predictor_prompts import (
    DAILY_PREDICTOR_PROMPT,
    split_daily_predictor_prompt,
)
from local_autoresearch.live_session_store import DEFAULT_LIVE_SESSIONS_DB, load_live_sessions
from local_autoresearch.quant_analytics import (
    calculate_sized_trading_pnl,
    create_walk_forward_splits,
    format_normalized_quant_vector,
    passes_two_sided_gate_discrete,
)
from tasks.daily_autoresearch import calculate_daily_ratchet_metrics
from tasks.evaluate_daily_predictions import calculate_brier_score, compute_intraday_hit_metrics

DEFAULT_STRATA_URL = os.getenv("STRATA_BASE_URL", "http://127.0.0.1:8080/v1")
DEFAULT_STRATA_MODEL = os.getenv("STRATA_MODEL", "orcarouter-qwen3.8-flash-next-uncensored-iq3_xxs")


def extract_daily_prediction(raw_text: str) -> dict[str, Any]:
    """Extract structured prediction from Qwen output, handling <think> tags, fences, and fallbacks."""
    clean_text = re.sub(r"<think>[\s\S]*?</think>", "", raw_text or "").strip()
    if not clean_text:
        clean_text = raw_text or ""

    data: dict[str, Any] | None = None

    # 1. Search for fenced JSON ```json ... ```
    json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", clean_text)
    if json_match:
        with contextlib.suppress(Exception):
            data = json.loads(json_match.group(1))

    # 2. Search for outermost raw JSON { ... }
    if not data:
        bracket_match = re.search(r"(\{[\s\S]*\})", clean_text)
        if bracket_match:
            with contextlib.suppress(Exception):
                data = json.loads(bracket_match.group(1))

    direction = "UP"
    confidence = 50.0
    expected_return_pct = 0.0
    rationale = "Parsed from local model completion."
    catalysts: list[str] = []

    if data and isinstance(data, dict):
        raw_dir = str(data.get("predicted_direction") or data.get("direction") or "").strip().upper()
        if raw_dir in ("UP", "DOWN"):
            direction = raw_dir

        raw_conf = data.get("confidence")
        if raw_conf is not None:
            with contextlib.suppress(ValueError, TypeError):
                c_val = float(raw_conf)
                confidence = round(c_val * 100.0, 1) if c_val <= 1.0 else round(c_val, 1)

        raw_exp = data.get("expected_return_pct")
        if raw_exp is not None:
            with contextlib.suppress(ValueError, TypeError):
                expected_return_pct = round(float(raw_exp), 2)

        if data.get("rationale"):
            rationale = str(data["rationale"]).strip()

        if isinstance(data.get("catalysts"), list):
            catalysts = [str(c) for c in data["catalysts"]]

    return {
        "predicted_direction": direction,
        "confidence": confidence,
        "expected_return_pct": expected_return_pct,
        "rationale": rationale,
        "catalysts": catalysts,
    }


def evaluate_prediction_record(session: dict[str, Any], prediction: dict[str, Any]) -> dict[str, Any]:
    """Score a single session prediction against ground-truth market results."""
    pred_dir = str(prediction.get("predicted_direction", "UP")).upper()
    actual_dir = str(session.get("actual_direction", "")).upper()
    is_correct = pred_dir == actual_dir

    confidence = float(prediction.get("confidence", 50.0))
    expected_return_pct = prediction.get("expected_return_pct")

    brier = calculate_brier_score(
        predicted_direction=pred_dir,
        confidence=confidence,
        actual_direction=actual_dir,
    )

    open_p = float(session.get("open_price") or 0.0)
    high_p = float(session.get("high_price") or open_p)
    low_p = float(session.get("low_price") or open_p)
    close_p = float(session.get("close_price") or open_p)

    intraday_hit, intraday_direction_hit = compute_intraday_hit_metrics(
        predicted_direction=pred_dir,
        expected_return_pct=expected_return_pct,
        open_price=open_p,
        high_price=high_p,
        low_price=low_p,
    )

    return {
        "target_date": session.get("target_date"),
        "ticker": session.get("ticker", "SPY"),
        "open_price": open_p,
        "close_price": close_p,
        "high_price": high_p,
        "low_price": low_p,
        "actual_direction": actual_dir,
        "predicted_direction": pred_dir,
        "confidence": confidence,
        "expected_return_pct": expected_return_pct,
        "rationale": prediction.get("rationale", ""),
        "catalysts": prediction.get("catalysts", []),
        "is_correct": is_correct,
        "brier_score": round(brier, 4),
        "intraday_hit": intraday_hit,
        "intraday_direction_hit": intraday_direction_hit,
    }


def should_prune_stage1(
    evaluated: int,
    correct: int,
    min_win_rate: float = 0.52,
    sieve_size: int = 25,
    records: list[dict[str, Any]] | None = None,
    min_sharpe: float = -0.5,
    min_balanced_acc: float = 48.0,
    min_single_class_recall: float = 25.0,
) -> bool:
    """Determine whether to prune candidate at Stage 1 screening sieve.

    Evaluates directional win rate, confidence-sized Sharpe return, and class balance
    to prune reckless drawdowns and one-sided asymmetric collapses early.
    """
    if evaluated < sieve_size:
        return False
    win_rate = correct / evaluated if evaluated > 0 else 0.0
    if win_rate < min_win_rate:
        return True

    if records and len(records) >= sieve_size:
        sized_pnl = calculate_sized_trading_pnl(records[:sieve_size])
        ann_sharpe = float(sized_pnl.get("annualized_sharpe", 0.0))
        if ann_sharpe < min_sharpe:
            return True

        bal_metrics = calculate_balanced_accuracy(records[:sieve_size])
        if bal_metrics["balanced_accuracy_pct"] < min_balanced_acc:
            return True
        if (
            bal_metrics["recall_up_pct"] < min_single_class_recall
            or bal_metrics["recall_down_pct"] < min_single_class_recall
        ):
            return True

    return False


def calculate_balanced_accuracy(records: list[dict[str, Any]]) -> dict[str, float]:
    """Calculate class-balanced accuracy and Matthews Correlation Coefficient."""
    if not records:
        return {
            "balanced_accuracy_pct": 0.0,
            "win_rate_pct": 0.0,
            "recall_up_pct": 0.0,
            "recall_down_pct": 0.0,
            "mcc": 0.0,
        }

    tp = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "UP" and str(r.get("actual_direction", "")).upper() == "UP"
    )
    tn = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "DOWN"
        and str(r.get("actual_direction", "")).upper() == "DOWN"
    )
    fp = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "UP"
        and str(r.get("actual_direction", "")).upper() == "DOWN"
    )
    fn = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "DOWN"
        and str(r.get("actual_direction", "")).upper() == "UP"
    )

    total = len(records)
    recall_up = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    recall_down = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_acc = 0.5 * (recall_up + recall_down) * 100.0

    denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = ((tp * tn) - (fp * fn)) / denom if denom > 0 else 0.0

    return {
        "balanced_accuracy_pct": round(balanced_acc, 2),
        "win_rate_pct": round((tp + tn) / total * 100.0, 2) if total > 0 else 0.0,
        "recall_up_pct": round(recall_up * 100.0, 2),
        "recall_down_pct": round(recall_down * 100.0, 2),
        "mcc": round(mcc, 4),
    }


def lint_mutant_prompt(prompt_text: str) -> tuple[bool, str | None]:
    """Ensure candidate strategy prompt contains no date-anchoring or temporal leakage."""
    # Check 4-digit years
    if re.search(r"\b202[0-9]\b", prompt_text):
        return False, "Prompt contains explicit calendar year reference"

    # Check month + day combinations (e.g. August 26, Sep 15)
    months_pat = (
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+[0-9]{1,2}\b"
    )
    if re.search(months_pat, prompt_text, re.IGNORECASE):
        return False, "Prompt contains specific calendar date reference"

    # Check ISO format dates
    if re.search(r"\b[0-9]{4}-[0-9]{2}-[0-9]{2}\b", prompt_text):
        return False, "Prompt contains ISO date reference"

    return True, None


def passes_two_sided_gate(
    bal_metrics: dict[str, float],
    min_recall_up: float = 54.0,
    min_recall_down: float = 54.0,
    min_bal_acc: float = 58.0,
    min_mcc: float = 0.20,
) -> tuple[bool, str]:
    """Validate that candidate exhibits genuine two-sided predictive edge (no perma-bear or perma-bull gaming)."""
    return passes_two_sided_gate_discrete(
        bal_metrics=bal_metrics,
        min_recall_up=min_recall_up,
        min_recall_down=min_recall_down,
        min_bal_acc=min_bal_acc,
        min_mcc=min_mcc,
    )


def split_sessions_walk_forward(
    sessions: list[dict[str, Any]],
    n_splits: int = 3,
    min_train_size: int = 10,
) -> list[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    """Generate expanding-window walk-forward cross validation folds over sessions."""
    return create_walk_forward_splits(sessions, n_splits=n_splits, min_train_size=min_train_size)


def create_balanced_stratified_split(
    sessions: list[dict[str, Any]],
    train_ratio: float = 0.7,
    seed: int = 42,
    shuffle_order: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Create a strictly balanced (1:1 UP vs DOWN) train and test partition to eliminate base-rate distortion.

    When shuffle_order is True (default), dates in train and test partitions are pseudo-randomly
    interleaved to evaluate non-contiguous timeframes, preventing contiguous timeframe regime traps.
    When False, partitions are strictly sorted chronologically.
    """
    import random

    ups = [s for s in sessions if str(s.get("actual_direction", "")).upper() == "UP"]
    downs = [s for s in sessions if str(s.get("actual_direction", "")).upper() == "DOWN"]

    rng = random.Random(seed)
    rng.shuffle(ups)
    rng.shuffle(downs)

    # Subsample to the minority class count for exact 1:1 balance
    min_count = min(len(ups), len(downs))
    balanced_ups = ups[:min_count]
    balanced_downs = downs[:min_count]

    split_count = int(min_count * train_ratio)

    train = balanced_ups[:split_count] + balanced_downs[:split_count]
    test = balanced_ups[split_count:] + balanced_downs[split_count:]

    if shuffle_order:
        rng.shuffle(train)
        rng.shuffle(test)
    else:
        train.sort(key=lambda s: s.get("target_date", ""))
        test.sort(key=lambda s: s.get("target_date", ""))

    return train, test


def create_stratified_split(
    sessions: list[dict[str, Any]],
    train_ratio: float = 0.7,
    seed: int = 42,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Deterministically partition sessions into stratified in-sample and out-of-sample sets."""
    import random

    ups = [s for s in sessions if str(s.get("actual_direction", "")).upper() == "UP"]
    downs = [s for s in sessions if str(s.get("actual_direction", "")).upper() == "DOWN"]

    rng = random.Random(seed)
    rng.shuffle(ups)
    rng.shuffle(downs)

    split_up = int(len(ups) * train_ratio)
    split_down = int(len(downs) * train_ratio)

    train = ups[:split_up] + downs[:split_down]
    test = ups[split_up:] + downs[split_down:]

    train.sort(key=lambda s: s.get("target_date", ""))
    test.sort(key=lambda s: s.get("target_date", ""))

    return train, test


def is_statistically_significant_improvement(wins: int, total: int, alpha: float = 0.05) -> tuple[bool, float]:
    """Execute exact one-tailed binomial test against 50% coin-flip null hypothesis."""
    if total <= 0:
        return False, 1.0
    res = binomtest(wins, total, p=0.5, alternative="greater")
    p_val = float(res.pvalue)
    return p_val < alpha, p_val


def format_single_prompt_user_message(session: dict[str, Any]) -> str:
    """Format single-pass prediction user prompt with standardized quantitative feature conditioning."""
    payload = session.get("evaluation_payload") or ""
    quant_block = format_normalized_quant_vector(session)
    ticker = session.get("ticker", "SPY")

    context_parts: list[str] = []
    if quant_block and "Not Provided / N/A" not in quant_block:
        context_parts.append(quant_block)
    if payload:
        context_parts.append(f"Market Context:\n{payload}")
    else:
        context_parts.append("Market Context:\nNone")

    full_context = "\n\n".join(context_parts)
    return (
        f"{full_context}\n\n"
        f"Analyze the market context and predict whether {ticker} will close HIGHER (UP) or LOWER (DOWN) "
        f"at 4:00 PM ET today compared to the 9:30 AM ET Open price."
    )


async def query_strata_chat(
    client: httpx.AsyncClient,
    system_prompt: str,
    user_prompt: str,
    base_url: str = DEFAULT_STRATA_URL,
    model: str = DEFAULT_STRATA_MODEL,
    temperature: float = 0.3,
    max_tokens: int = 16384,
    reasoning_budget_tokens: int = -1,
) -> str:
    """Query Strata OpenAI-compatible chat completion endpoint with 16k max tokens and unconstrained reasoning (-1)."""
    url = f"{base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning_budget_tokens": reasoning_budget_tokens,
    }
    resp = await client.post(url, json=payload, timeout=500.0)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


async def evaluate_prompt_on_live_sessions(
    prompt_content: str,
    sessions: list[dict[str, Any]],
    client: httpx.AsyncClient | None = None,
    stage1_sieve: int = 25,
    min_stage1_win_rate: float = 0.52,
) -> dict[str, Any]:
    """Run single-prompt evaluation over live sessions with Stage 1 early pruning."""
    if not sessions:
        return {"pruned": True, "reason": "No sessions provided", "metrics": {}}

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=600.0)
        owns_client = True

    eval_records: list[dict[str, Any]] = []
    correct_count = 0

    try:
        for idx, session in enumerate(sessions):
            user_msg = format_single_prompt_user_message(session)
            raw_response = await query_strata_chat(client, prompt_content, user_msg)
            pred = extract_daily_prediction(raw_response)
            rec = evaluate_prediction_record(session, pred)
            eval_records.append(rec)
            if rec["is_correct"]:
                correct_count += 1

            status_str = "HIT" if rec["is_correct"] else "MISS"
            logger.info(
                f"[{idx + 1:02d}/{len(sessions):02d}] {session['target_date']} | "
                f"Pred: {rec['predicted_direction']} (Conf: {rec['confidence']}%) | "
                f"Actual: {rec['actual_direction']} ({status_str}) | "
                f"WR: {correct_count / (idx + 1):.1%} ({correct_count}/{idx + 1})"
            )

            # Check Stage 1 early pruning
            if idx + 1 == stage1_sieve and should_prune_stage1(
                evaluated=idx + 1,
                correct=correct_count,
                min_win_rate=min_stage1_win_rate,
                sieve_size=stage1_sieve,
                records=eval_records,
            ):
                win_rate = correct_count / (idx + 1)
                metrics = calculate_daily_ratchet_metrics(eval_records)
                sized_pnl = calculate_sized_trading_pnl(eval_records)
                ann_sharpe = sized_pnl.get("annualized_sharpe", 0.0)
                bal_metrics = calculate_balanced_accuracy(eval_records)
                return {
                    "pruned": True,
                    "reason": (
                        f"Stage 1 pruned: win rate {win_rate:.1%} < {min_stage1_win_rate:.1%}, "
                        f"Sharpe ({ann_sharpe:.2f}), or asymmetric collapse "
                        f"(BalAcc {bal_metrics['balanced_accuracy_pct']}%, UP {bal_metrics['recall_up_pct']}%, DOWN {bal_metrics['recall_down_pct']}%)"
                    ),
                    "evaluated_count": len(eval_records),
                    "metrics": metrics,
                    "records": eval_records,
                }

        metrics = calculate_daily_ratchet_metrics(eval_records)
        sized_pnl = calculate_sized_trading_pnl(eval_records)
        is_sig, p_val = is_statistically_significant_improvement(wins=correct_count, total=len(eval_records))
        return {
            "pruned": False,
            "reason": None,
            "evaluated_count": len(eval_records),
            "correct_count": correct_count,
            "win_rate": correct_count / len(eval_records) if eval_records else 0.0,
            "metrics": metrics,
            "sized_pnl": sized_pnl,
            "is_significant": is_sig,
            "p_value": round(p_val, 4),
            "records": eval_records,
        }
    finally:
        if owns_client:
            await client.aclose()


def extract_mutant_strategy_payload(clean_text: str) -> dict[str, Any] | None:
    """Robustly extract hypothesis and new_strategy from meta-researcher completion."""
    # 1. Try ```json ... ``` block with unescaped newlines support
    json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", clean_text)
    if json_match:
        with contextlib.suppress(Exception):
            return json.loads(json_match.group(1), strict=False)

    # 2. Try outermost { ... }
    bracket_match = re.search(r"(\{[\s\S]*\})", clean_text)
    if bracket_match:
        with contextlib.suppress(Exception):
            return json.loads(bracket_match.group(1), strict=False)

    # 3. Fallback: Regex extraction of hypothesis and new_strategy fields directly
    hyp_m = re.search(r'"hypothesis":\s*"([^"\\]*(?:\\.[^"\\]*)*)"', clean_text)
    strat_m = re.search(r'"new_strategy":\s*"([\s\S]*?)"\s*\}', clean_text)
    if strat_m:
        hypothesis = hyp_m.group(1) if hyp_m else "Evolved strategy via Strata meta-researcher."
        new_strategy = strat_m.group(1).replace("\\n", "\n").replace('\\"', '"')
        return {"hypothesis": hypothesis, "new_strategy": new_strategy}

    # 4. Fallback: Raw analytical strategy block
    if "=== ANALYTICAL STRATEGY" in clean_text or "=== TWO-SIDED" in clean_text:
        return {
            "hypothesis": "Extracted strategy blocks from meta-researcher response.",
            "new_strategy": clean_text.strip(),
        }

    return None


async def mutate_daily_strategy(
    current_prompt: str,
    evaluated_records: list[dict[str, Any]],
    client: httpx.AsyncClient,
    is_radical: bool = False,
) -> tuple[str, str]:
    """Query Strata meta-researcher to mutate the mutable strategy section of DAILY_PREDICTOR_PROMPT."""
    header, mutable, footer = split_daily_predictor_prompt(current_prompt)

    # Compile anonymized balanced error analysis (both false UPs and false DOWNs)
    false_ups = [
        r
        for r in evaluated_records
        if not r.get("is_correct") and str(r.get("predicted_direction", "")).upper() == "UP"
    ]
    false_downs = [
        r
        for r in evaluated_records
        if not r.get("is_correct") and str(r.get("predicted_direction", "")).upper() == "DOWN"
    ]
    misses = false_ups[:3] + false_downs[:3]
    miss_summaries = []
    for idx, m in enumerate(misses):
        open_p = float(m.get("open_price") or 0.0)
        close_p = float(m.get("close_price") or 0.0)
        ret_pct = ((close_p - open_p) / open_p * 100.0) if open_p > 0 else 0.0
        miss_summaries.append(
            f"- Scenario {idx + 1}: Predicted {m.get('predicted_direction')} (Conf: {m.get('confidence')}%), "
            f"but actual market move was {m.get('actual_direction')} ({ret_pct:+.2f}%). "
            f'Prior reasoning was: "{m.get("rationale", "")[:120]}"'
        )
    miss_text = "\n".join(miss_summaries) if miss_summaries else "No significant misses recorded."

    radical_block = ""
    if is_radical:
        radical_block = """
=== RADICAL EXPLORATION DIRECTIVE (ESCAPE LOCAL OPTIMA) ===
The tournament is actively testing bold alternative market paradigms to break out of local optima plateaus.
DO NOT make minor incremental tweaks. Propose a fundamental re-architecture of the strategy instructions.
Anchor the rules around one of the following high-alpha structural mechanisms:
1. Cross-Asset Yield Transmission: Priority weighting on 10Y/2Y Treasury yield changes (TLT/IEF momentum) and commodity inflation (GLD/USO) vs equity futures.
2. Derivatives Positioning & Volatility Skew: Rules derived strictly from 25-delta Put/Call skew, Max Pain strike gravitation, and institutional options flow.
3. Asymmetric Gap-Fill Reversal: Mandatory fading of large overnight futures gaps when opening market internals or breadth (QQQ/IWM) fail to confirm continuation.
4. Market Regime Classification: Classify today's pre-market state into 1 of 4 regimes (Low-Vol Pin, Trend Expansion, Mean Reversion, Catalyst Shock) before predicting direction.
5. Dealer Gamma & Max Pain Pinning: Check options open interest walls and Max Pain strike to avoid mistaking compression for directional breakouts.
6. Anti-Pessimism Base-Rate Prior: Evaluate historical ~54% green base-rate prior to prevent false DOWN calls on generic macro headlines.
7. Dialectical Balance-Sheet Deliberation: Mandatory two-column conviction scoring (Bull [1-10] vs Bear [1-10]). If delta <= 1, default to consolidation/pin with low confidence (52-54%).
8. Regime-Gated Confidence Clamping: Clamp confidence to 52-55% in low-volatility or Max Pain pin environments; reserve >60% confidence strictly for confirmed cross-asset divergence.
"""

    meta_prompt = f"""You are an elite quantitative meta-researcher optimizing an intraday SPY directional trading prompt.
Your goal is to rewrite ONLY the middle strategy section of the system prompt to eliminate false predictions and achieve balanced, two-sided predictive accuracy.

=== CURRENT MUTABLE STRATEGY ===
{mutable}
{radical_block}
=== ANTI-WHIPLASH SYMMETRY MANDATE ===
Do NOT cure missed UP calls by penalizing DOWN calls or raising the hurdle for DOWN to impossible levels.
Do NOT cure missed DOWN calls by penalizing UP calls or raising the hurdle for UP to impossible levels.
In an intraday zero-mean market, directional symmetry is non-negotiable. Both UP and DOWN must require identical evidentiary standards.
Any strategy that produces >70% calls in a single direction will be rejected by the mandatory two-sided recall gate (min 54.0% recall on BOTH sides).

=== RECENT ANONYMIZED PREDICTION MISSES & ERRORS (GROUND TRUTH) ===
{miss_text}

=== INSTRUCTIONS ===
1. Analyze the false predictions above. Identify why the model erred (e.g. failing to respect bond yield moves, misjudging gap-fill exhaustion, positive framing bias).
2. Formulate a specific causal hypothesis to eliminate these errors.
3. Rewrite the strategy section with sharp, falsifiable, symmetrical rules for both UP and DOWN days. Enforce dialectical balance so neither side is suppressed.
4. CRITICAL: Never include specific dates, years, or day numbers in your strategy. Rules must be universal and macro-driven.
5. Do NOT output header or JSON schema blocks; they are frozen and appended automatically.
6. Output MUST be valid JSON formatted as:
{{
  "hypothesis": "<1-2 sentence concise causal reasoning>",
  "new_strategy": "<full text of new strategy instructions>"
}}
"""
    raw_meta = await query_strata_chat(
        client,
        "You are an expert quantitative researcher. Output valid JSON only.",
        meta_prompt,
        temperature=0.95 if is_radical else 0.7,
    )

    clean_meta = re.sub(r"<think>[\s\S]*?</think>", "", raw_meta).strip()
    payload = extract_mutant_strategy_payload(clean_meta)

    if payload and isinstance(payload, dict) and payload.get("new_strategy"):
        new_strategy = str(payload["new_strategy"]).strip()
        hypothesis = str(payload.get("hypothesis", "Evolved strategy via Strata meta-researcher."))
        assembled = f"{header}\n\n{new_strategy}\n\n{footer}"
        is_clean, reason = lint_mutant_prompt(assembled)
        if not is_clean:
            logger.warning(f"Mutant prompt rejected by anti-memorization linter: {reason}")
            return current_prompt, f"Linter rejected mutant prompt: {reason}"
        return assembled, hypothesis

    return current_prompt, "Mutation failed to produce valid JSON strategy; keeping existing prompt."


DEFAULT_RATCHET_STATE_PATH = ".single_prompt_ratchet_state.json"
DEFAULT_RATCHET_JOURNAL_PATH = ".single_prompt_ratchet_journal.md"


def compute_quant_diagnostics(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate comprehensive institutional quant and ML metrics for a prediction run."""
    if not records:
        return {}

    total = len(records)
    tp = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "UP" and str(r.get("actual_direction", "")).upper() == "UP"
    )
    tn = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "DOWN"
        and str(r.get("actual_direction", "")).upper() == "DOWN"
    )
    fp = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "UP"
        and str(r.get("actual_direction", "")).upper() == "DOWN"
    )
    fn = sum(
        1
        for r in records
        if str(r.get("predicted_direction", "")).upper() == "DOWN"
        and str(r.get("actual_direction", "")).upper() == "UP"
    )

    wins = tp + tn
    win_rate = wins / total if total > 0 else 0.0

    recall_up = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    recall_down = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    balanced_acc = 0.5 * (recall_up + recall_down) * 100.0

    prec_up = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    prec_down = tn / (tn + fn) if (tn + fn) > 0 else 0.0

    denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    mcc = ((tp * tn) - (fp * fn)) / denom if denom > 0 else 0.0

    brier_scores = [float(r.get("brier_score", 0.25)) for r in records]
    mean_brier = sum(brier_scores) / total if total > 0 else 0.25

    kelly_fraction = max(0.0, 2 * win_rate - 1)
    _, p_val = is_statistically_significant_improvement(wins, total)
    sized_pnl = calculate_sized_trading_pnl(records)

    return {
        "total_evaluated": total,
        "correct_predictions": wins,
        "win_rate_pct": round(win_rate * 100.0, 2),
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "recall_up_pct": round(recall_up * 100.0, 2),
        "recall_down_pct": round(recall_down * 100.0, 2),
        "precision_up_pct": round(prec_up * 100.0, 2),
        "precision_down_pct": round(prec_down * 100.0, 2),
        "balanced_accuracy_pct": round(balanced_acc, 2),
        "mcc": round(mcc, 4),
        "mean_brier": round(mean_brier, 4),
        "kelly_fraction": round(kelly_fraction, 4),
        "p_value": round(p_val, 4),
        "annualized_sharpe": sized_pnl.get("annualized_sharpe", 0.0),
        "sized_cumulative_return_pct": sized_pnl.get("cumulative_return_pct", 0.0),
        "profit_factor": sized_pnl.get("profit_factor", 0.0),
        "max_drawdown_pct": sized_pnl.get("max_drawdown_pct", 0.0),
    }


def append_quant_journal_entry(
    journal_path: str,
    iteration: int,
    mode: str,
    hypothesis: str,
    status: str,
    champ_score: float,
    mutant_score: float,
    in_sample_diag: dict[str, Any],
    oos_diag: dict[str, Any] | None = None,
    reason: str | None = None,
) -> None:
    """Append a structured quantitative journal entry to markdown."""
    import time

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
    entry = [
        f"\n## Iteration {iteration}: {mode} — Status: {status.upper()}",
        f"- **Timestamp**: `{timestamp}`",
        f"- **Hypothesis**: *{hypothesis}*",
        f"- **In-Sample Score**: `{mutant_score:.2f}` (Champion: `{champ_score:.2f}`)",
        f"- **Verdict / Reason**: {reason or 'Evaluation completed.'}",
        "",
        "### In-Sample Quantitative Diagnostics",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| **Evaluated (TP/TN/FP/FN)** | {in_sample_diag.get('total_evaluated')} (TP={in_sample_diag.get('tp')}, TN={in_sample_diag.get('tn')}, FP={in_sample_diag.get('fp')}, FN={in_sample_diag.get('fn')}) |",
        f"| **Win Rate** | `{in_sample_diag.get('win_rate_pct', 0.0):.1f}%` ({in_sample_diag.get('correct_predictions')}/{in_sample_diag.get('total_evaluated')}) |",
        f"| **Balanced Accuracy** | `{in_sample_diag.get('balanced_accuracy_pct', 0.0):.1f}%` |",
        f"| **Recall UP / Recall DOWN** | `{in_sample_diag.get('recall_up_pct', 0.0):.1f}%` / `{in_sample_diag.get('recall_down_pct', 0.0):.1f}%` |",
        f"| **Precision UP / DOWN** | `{in_sample_diag.get('precision_up_pct', 0.0):.1f}%` / `{in_sample_diag.get('precision_down_pct', 0.0):.1f}%` |",
        f"| **Matthews Corr (MCC)** | `{in_sample_diag.get('mcc', 0.0):.3f}` |",
        f"| **Annualized Sharpe Ratio** | `{in_sample_diag.get('annualized_sharpe', 0.0):.2f}` |",
        f"| **Sized Return / Max DD** | `{in_sample_diag.get('sized_cumulative_return_pct', 0.0):+.2f}%` / `{in_sample_diag.get('max_drawdown_pct', 0.0):.2f}%` |",
        f"| **Profit Factor** | `{in_sample_diag.get('profit_factor', 0.0):.2f}` |",
        f"| **Mean Brier Score** | `{in_sample_diag.get('mean_brier', 0.0):.4f}` |",
        f"| **Kelly Fraction ($f^*$)** | `{in_sample_diag.get('kelly_fraction', 0.0):.4f}` |",
        f"| **Binomial $p$-value** | `{in_sample_diag.get('p_value', 1.0):.4f}` |",
        "",
    ]
    if oos_diag:
        entry.extend(
            [
                "### Out-of-Sample Holdout Diagnostics",
                "| Metric | Value |",
                "| :--- | :--- |",
                f"| **OOS Evaluated** | {oos_diag.get('total_evaluated')} (TP={oos_diag.get('tp')}, TN={oos_diag.get('tn')}, FP={oos_diag.get('fp')}, FN={oos_diag.get('fn')}) |",
                f"| **OOS Win Rate** | `{oos_diag.get('win_rate_pct', 0.0):.1f}%` |",
                f"| **OOS Balanced Accuracy** | `{oos_diag.get('balanced_accuracy_pct', 0.0):.1f}%` |",
                f"| **OOS Recall UP / DOWN** | `{oos_diag.get('recall_up_pct', 0.0):.1f}%` / `{oos_diag.get('recall_down_pct', 0.0):.1f}%` |",
                f"| **OOS MCC** | `{oos_diag.get('mcc', 0.0):.3f}` |",
                "",
            ]
        )
    entry.append("---\n")
    with open(journal_path, "a") as f:
        f.write("\n".join(entry))


DEFAULT_RATCHET_STATE_PATH = ".single_prompt_ratchet_state.json"


async def run_single_prompt_tournament(
    iterations: int = 10,
    db_path: str = DEFAULT_LIVE_SESSIONS_DB,
    state_path: str = DEFAULT_RATCHET_STATE_PATH,
    journal_path: str = DEFAULT_RATCHET_JOURNAL_PATH,
    stage1_sieve: int = 15,
    min_stage1_win_rate: float = 0.52,
    promising_win_rate: float = 0.58,
    min_holdout_balanced_acc: float = 55.0,
    balanced_sessions: bool = True,
    only_baseline: bool = False,
    force_radical: bool = False,
) -> dict[str, Any]:
    """Execute single-prompt autoresearch tournament across leak-free live production sessions."""
    sessions = load_live_sessions(db_path)
    if not sessions:
        logger.error(f"No live production sessions found in {db_path}. Run live_session_store.py first.")
        return {}

    if balanced_sessions:
        train_sessions, holdout_sessions = create_balanced_stratified_split(sessions, train_ratio=0.7, seed=42)
        logger.info(
            f"Partitioned {len(train_sessions) + len(holdout_sessions)} balanced (1:1 UP/DOWN) clean sessions: "
            f"{len(train_sessions)} In-Sample Training and {len(holdout_sessions)} Out-of-Sample Holdout."
        )
    else:
        train_sessions, holdout_sessions = create_stratified_split(sessions, train_ratio=0.68, seed=42)
        logger.info(
            f"Partitioned {len(sessions)} clean sessions: {len(train_sessions)} In-Sample Training "
            f"and {len(holdout_sessions)} Out-of-Sample Holdout."
        )

    state: dict[str, Any] = {}
    if os.path.exists(state_path):
        with contextlib.suppress(Exception), open(state_path) as f:
            state = json.load(f)

    async with httpx.AsyncClient(timeout=600.0) as client:
        # 1. Establish or load baseline
        if not state.get("champion_prompt"):
            logger.info(
                f"Evaluating default DAILY_PREDICTOR_PROMPT baseline on In-Sample ({len(train_sessions)} sessions)..."
            )
            train_eval = await evaluate_prompt_on_live_sessions(
                prompt_content=DAILY_PREDICTOR_PROMPT,
                sessions=train_sessions,
                client=client,
                stage1_sieve=len(train_sessions) + 1,  # Do not prune baseline
            )
            train_bal = calculate_balanced_accuracy(train_eval.get("records", []))
            train_diag = compute_quant_diagnostics(train_eval.get("records", []))

            logger.info(
                f"Evaluating default DAILY_PREDICTOR_PROMPT baseline on Out-of-Sample Holdout ({len(holdout_sessions)} sessions)..."
            )
            holdout_eval = await evaluate_prompt_on_live_sessions(
                prompt_content=DAILY_PREDICTOR_PROMPT,
                sessions=holdout_sessions,
                client=client,
                stage1_sieve=len(holdout_sessions) + 1,
            )
            holdout_bal = calculate_balanced_accuracy(holdout_eval.get("records", []))
            oos_diag = compute_quant_diagnostics(holdout_eval.get("records", []))

            state = {
                "champion_prompt": DAILY_PREDICTOR_PROMPT,
                "champion_score": train_eval["metrics"].get("score", 0.0),
                "champion_win_rate": train_eval.get("win_rate", 0.0),
                "champion_balanced_acc": train_bal["balanced_accuracy_pct"],
                "champion_mcc": train_bal["mcc"],
                "champion_metrics": train_eval.get("metrics", {}),
                "evaluated_records": train_eval.get("records", []),
                "holdout_win_rate": holdout_eval.get("win_rate", 0.0),
                "holdout_balanced_acc": holdout_bal["balanced_accuracy_pct"],
                "holdout_mcc": holdout_bal["mcc"],
                "consecutive_rejections": 0,
                "history": [],
            }
            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)

            append_quant_journal_entry(
                journal_path=journal_path,
                iteration=0,
                mode="BASELINE CALIBRATION",
                hypothesis="Initial production prompt baseline evaluation.",
                status="baseline_established",
                champ_score=state["champion_score"],
                mutant_score=state["champion_score"],
                in_sample_diag=train_diag,
                oos_diag=oos_diag,
                reason="Calibrated ground-truth baseline established.",
            )

            logger.info(
                f"Baseline Established: In-Sample Score={state['champion_score']:.2f} | "
                f"Win Rate={state['champion_win_rate']:.1%} | Balanced Acc={state['champion_balanced_acc']:.1f}% | MCC={state['champion_mcc']:.3f} | "
                f"Holdout Balanced Acc={state['holdout_balanced_acc']:.1f}%"
            )

        if only_baseline:
            return state

        # 2. Tournament Optimization Loop
        champ_prompt = state["champion_prompt"]
        champ_score = float(state["champion_score"])
        champ_bal_acc = float(state.get("champion_balanced_acc", 50.0))
        champ_records = state.get("evaluated_records", [])
        consecutive_rejections = int(state.get("consecutive_rejections", 0))

        for i in range(1, iterations + 1):
            is_radical = force_radical or (consecutive_rejections >= 2) or (i % 4 == 0)
            mode_str = "RADICAL EXPLORATION" if is_radical else "INCREMENTAL REFINEMENT"
            iter_index = len(state.get("history", [])) + 1
            logger.info(f"=== [Iteration {iter_index} (Run Step {i}/{iterations})] Mutating Strategy ({mode_str}) ===")
            mutant_prompt, hypothesis = await mutate_daily_strategy(
                champ_prompt, champ_records, client, is_radical=is_radical
            )
            logger.info(f"Hypothesis: {hypothesis}")

            res = await evaluate_prompt_on_live_sessions(
                prompt_content=mutant_prompt,
                sessions=train_sessions,
                client=client,
                stage1_sieve=stage1_sieve,
                min_stage1_win_rate=min_stage1_win_rate,
            )

            in_sample_records = res.get("records", [])
            in_sample_diag = compute_quant_diagnostics(in_sample_records)

            if res.get("pruned"):
                consecutive_rejections += 1
                state["consecutive_rejections"] = consecutive_rejections
                logger.info(f"Candidate rejected: {res.get('reason')}")
                state.setdefault("history", []).append(
                    {
                        "iteration": iter_index,
                        "hypothesis": hypothesis,
                        "mode": mode_str,
                        "status": "pruned",
                        "reason": res.get("reason"),
                    }
                )
                append_quant_journal_entry(
                    journal_path=journal_path,
                    iteration=iter_index,
                    mode=mode_str,
                    hypothesis=hypothesis,
                    status="pruned",
                    champ_score=champ_score,
                    mutant_score=float(res.get("metrics", {}).get("score", 0.0)),
                    in_sample_diag=in_sample_diag,
                    reason=res.get("reason"),
                )
                with open(state_path, "w") as f:
                    json.dump(state, f, indent=2)
                continue

            mutant_score = float(res["metrics"].get("score", 0.0))
            mutant_bal_metrics = calculate_balanced_accuracy(in_sample_records)
            mutant_bal_acc = mutant_bal_metrics["balanced_accuracy_pct"]
            is_sig = res.get("is_significant", False)
            p_val = res.get("p_value", 1.0)

            logger.info(
                f"In-Sample Evaluated: Score={mutant_score:.2f} (Champ: {champ_score:.2f}) | "
                f"Balanced Acc={mutant_bal_acc:.1f}% (Champ: {champ_bal_acc:.1f}%) | "
                f"Recall UP={mutant_bal_metrics['recall_up_pct']:.1f}% | Recall DOWN={mutant_bal_metrics['recall_down_pct']:.1f}% | "
                f"MCC={mutant_bal_metrics['mcc']:.3f} | p={p_val:.4f} (sig={is_sig})"
            )

            # In-Sample Gate: Must beat champion score AND pass two-sided recall hurdles
            passes_gate, gate_reason = passes_two_sided_gate(
                mutant_bal_metrics,
                min_recall_up=55.0,
                min_recall_down=55.0,
                min_bal_acc=promising_win_rate * 100.0,
                min_mcc=0.20,
            )

            if mutant_score > champ_score and passes_gate:
                logger.info(
                    f"Candidate passed In-Sample Two-Sided Gate! Testing on Out-of-Sample Holdout ({len(holdout_sessions)} sessions)..."
                )
                holdout_res = await evaluate_prompt_on_live_sessions(
                    prompt_content=mutant_prompt,
                    sessions=holdout_sessions,
                    client=client,
                    stage1_sieve=len(holdout_sessions) + 1,
                )
                holdout_records = holdout_res.get("records", [])
                holdout_bal = calculate_balanced_accuracy(holdout_records)
                oos_diag = compute_quant_diagnostics(holdout_records)
                oos_acc = holdout_bal["balanced_accuracy_pct"]

                oos_passed, oos_reason = passes_two_sided_gate(
                    holdout_bal,
                    min_recall_up=50.0,
                    min_recall_down=50.0,
                    min_bal_acc=min_holdout_balanced_acc,
                    min_mcc=0.15,
                )

                if oos_passed:
                    consecutive_rejections = 0
                    state["consecutive_rejections"] = 0
                    logger.info(
                        f"*** PROMOTING NEW CHAMPION! In-Sample Score {champ_score:.2f} -> {mutant_score:.2f} | "
                        f"OOS Balanced Acc={oos_acc:.1f}% >= {min_holdout_balanced_acc:.1f}% ***"
                    )
                    champ_prompt = mutant_prompt
                    champ_score = mutant_score
                    champ_bal_acc = mutant_bal_acc
                    champ_records = in_sample_records
                    state["champion_prompt"] = champ_prompt
                    state["champion_score"] = champ_score
                    state["champion_win_rate"] = res.get("win_rate", 0.0)
                    state["champion_balanced_acc"] = mutant_bal_acc
                    state["champion_mcc"] = mutant_bal_metrics["mcc"]
                    state["champion_metrics"] = res.get("metrics", {})
                    state["evaluated_records"] = champ_records
                    state["holdout_balanced_acc"] = oos_acc
                    state.setdefault("history", []).append(
                        {
                            "iteration": iter_index,
                            "hypothesis": hypothesis,
                            "mode": mode_str,
                            "status": "promoted",
                            "score": mutant_score,
                            "in_sample_balanced_acc": mutant_bal_acc,
                            "oos_balanced_acc": oos_acc,
                            "p_value": p_val,
                        }
                    )
                    append_quant_journal_entry(
                        journal_path=journal_path,
                        iteration=iter_index,
                        mode=mode_str,
                        hypothesis=hypothesis,
                        status="promoted",
                        champ_score=champ_score,
                        mutant_score=mutant_score,
                        in_sample_diag=in_sample_diag,
                        oos_diag=oos_diag,
                        reason="Passed In-Sample score hurdle and OOS two-sided generalization gate.",
                    )
                else:
                    consecutive_rejections += 1
                    state["consecutive_rejections"] = consecutive_rejections
                    logger.info(f"Candidate rejected by OOS Gate: {oos_reason} (In-sample overfit)")
                    state.setdefault("history", []).append(
                        {
                            "iteration": iter_index,
                            "hypothesis": hypothesis,
                            "mode": mode_str,
                            "status": "oos_failed",
                            "score": mutant_score,
                            "in_sample_balanced_acc": mutant_bal_acc,
                            "oos_balanced_acc": oos_acc,
                            "reason": oos_reason,
                        }
                    )
                    append_quant_journal_entry(
                        journal_path=journal_path,
                        iteration=iter_index,
                        mode=mode_str,
                        hypothesis=hypothesis,
                        status="oos_failed",
                        champ_score=champ_score,
                        mutant_score=mutant_score,
                        in_sample_diag=in_sample_diag,
                        oos_diag=oos_diag,
                        reason=f"Failed OOS gate: {oos_reason}",
                    )
            else:
                consecutive_rejections += 1
                state["consecutive_rejections"] = consecutive_rejections
                reject_reason = (
                    gate_reason
                    if mutant_score > champ_score
                    else f"Score {mutant_score:.2f} <= Champ {champ_score:.2f}"
                )
                logger.info(f"Candidate rejected: {reject_reason}")
                state.setdefault("history", []).append(
                    {
                        "iteration": iter_index,
                        "hypothesis": hypothesis,
                        "mode": mode_str,
                        "status": "rejected",
                        "score": mutant_score,
                        "in_sample_balanced_acc": mutant_bal_acc,
                        "reason": reject_reason,
                    }
                )
                append_quant_journal_entry(
                    journal_path=journal_path,
                    iteration=iter_index,
                    mode=mode_str,
                    hypothesis=hypothesis,
                    status="rejected",
                    champ_score=champ_score,
                    mutant_score=mutant_score,
                    in_sample_diag=in_sample_diag,
                    reason=reject_reason,
                )

            with open(state_path, "w") as f:
                json.dump(state, f, indent=2)

    return state


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser(description="Single-Prompt Ground-Truth Ratchet Runner")
    parser.add_argument("--baseline", action="store_true", help="Only evaluate baseline prompt and exit")
    parser.add_argument("--iterations", type=int, default=8, help="Number of mutation iterations to run")
    parser.add_argument("--db-path", type=str, default=DEFAULT_LIVE_SESSIONS_DB, help="Path to SQLite sessions DB")
    parser.add_argument("--state-path", type=str, default=DEFAULT_RATCHET_STATE_PATH, help="Path to JSON state file")
    parser.add_argument(
        "--journal-path", type=str, default=DEFAULT_RATCHET_JOURNAL_PATH, help="Path to markdown journal"
    )
    parser.add_argument("--stage1-sieve", type=int, default=15, help="Number of sessions in Stage 1 sieve")
    parser.add_argument("--min-stage1-win-rate", type=float, default=0.52, help="Minimum win rate to pass Stage 1")
    parser.add_argument("--promising-win-rate", type=float, default=0.58, help="Minimum win rate for promotion")
    parser.add_argument("--balanced", dest="balanced", action="store_true", default=True, help="Use 1:1 balanced split")
    parser.add_argument("--no-balanced", dest="balanced", action="store_false", help="Use full imbalanced split")
    parser.add_argument("--radical", action="store_true", help="Force radical exploration mode on next iteration")

    args = parser.parse_args()

    asyncio.run(
        run_single_prompt_tournament(
            iterations=args.iterations,
            db_path=args.db_path,
            state_path=args.state_path,
            journal_path=args.journal_path,
            stage1_sieve=args.stage1_sieve,
            min_stage1_win_rate=args.min_stage1_win_rate,
            promising_win_rate=args.promising_win_rate,
            balanced_sessions=args.balanced,
            only_baseline=args.baseline,
            force_radical=args.radical,
        )
    )
