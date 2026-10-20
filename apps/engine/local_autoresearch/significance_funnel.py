"""Adaptive 3-Stage Significance Funnel for Double-Ratchet Local Autoresearch.

Enforces statistical rigor on candidate prompt pairs by escalating only promising
candidates (win rate >= 58.0% in Stage 1) to multi-regime expanded testing (Stage 2)
and validating with exact one-tailed binomial hypothesis testing against a 50% null
(p < 0.05).
"""

from __future__ import annotations

import math
import os
import random
import sys
from dataclasses import dataclass
from typing import Any

# Ensure apps/engine root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scipy import stats

from core.config import logger
from local_autoresearch.jev_evaluator import calculate_metrics
from local_autoresearch.manifest import JevCriteriaConfig


@dataclass
class SignificanceFunnelConfig:
    """Configuration parameters for the 3-Stage Adaptive Significance Funnel."""

    promising_win_rate: float = 0.58
    significance_alpha: float = 0.05
    stage2_expansion_weeks: int = 10
    enable_stage3: bool = True
    early_prune_stage2: bool = True


async def evaluate_curriculum_batch(*args: Any, **kwargs: Any) -> Any:
    """Delegates to double_ratchet.evaluate_curriculum_batch, avoiding circular import."""
    mod = sys.modules.get("local_autoresearch.double_ratchet")
    if mod and hasattr(mod, "evaluate_curriculum_batch"):
        return await mod.evaluate_curriculum_batch(*args, **kwargs)

    from local_autoresearch.double_ratchet import evaluate_curriculum_batch as _eval_batch

    return await _eval_batch(*args, **kwargs)


def calculate_binomial_significance(
    wins: int,
    total: int,
    null_prob: float = 0.5,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """Execute exact one-tailed binomial test against null hypothesis (default: random 50% coin flip)."""
    if total <= 0 or wins < 0:
        return {
            "wins": 0,
            "total": 0,
            "win_rate_pct": 0.0,
            "p_value": 1.0,
            "is_significant": False,
            "z_score": 0.0,
            "null_prob": null_prob,
            "alpha": alpha,
        }

    clamped_wins = min(wins, total)
    win_rate = clamped_wins / total
    win_rate_pct = round(win_rate * 100.0, 2)

    # Exact one-tailed binomial test: H0: p = null_prob vs H1: p > null_prob
    test_res = stats.binomtest(clamped_wins, total, null_prob, alternative="greater")
    p_value = round(float(test_res.pvalue), 6)

    # Standard normal approximation Z-score
    se = math.sqrt((null_prob * (1.0 - null_prob)) / total)
    z_score = round((win_rate - null_prob) / se, 4) if se > 0 else 0.0

    is_significant = (p_value <= alpha) and (win_rate > null_prob)

    return {
        "wins": clamped_wins,
        "total": total,
        "win_rate_pct": win_rate_pct,
        "p_value": p_value,
        "is_significant": is_significant,
        "z_score": z_score,
        "null_prob": null_prob,
        "alpha": alpha,
    }


def should_escalate_to_stage2(
    stage1_metrics: dict[str, Any],
    config: SignificanceFunnelConfig,
) -> bool:
    """Determine whether Stage 1 candidate merits multi-regime Stage 2 expansion."""
    if stage1_metrics.get("early_pruned", False):
        return False

    traded_days = stage1_metrics.get("traded_days", 0)
    if traded_days <= 0:
        return False

    wr = stage1_metrics.get("traded_win_rate_pct", 0.0) / 100.0
    return wr >= config.promising_win_rate


def sample_contrasting_regime_weeks(
    all_weeks: dict[str, list[dict[str, Any]]],
    stage1_week_keys: set[str],
    num_weeks: int = 10,
    seed: int | None = None,
) -> list[tuple[str, list[dict[str, Any]]]]:
    """Sample distinct, unseen weeks across diverse curriculum batches for Stage 2."""
    candidate_keys = [k for k in sorted(all_weeks.keys()) if k not in stage1_week_keys]
    if not candidate_keys:
        return []

    rng = random.Random(seed)
    chosen_keys = (
        rng.sample(candidate_keys, min(num_weeks, len(candidate_keys)))
        if len(candidate_keys) >= num_weeks
        else candidate_keys
    )
    # Sort chronologically for clean walk-forward evaluation
    chosen_keys.sort()
    return [(k, all_weeks[k]) for k in chosen_keys]


async def evaluate_stage2_escalation(
    expansion_weeks: list[tuple[str, list[dict[str, Any]]]],
    stage1_results: list[dict[str, Any]],
    ingestion_prompt: str,
    criteria: JevCriteriaConfig,
    config: SignificanceFunnelConfig,
    strata_url: str,
    laya_url: str | None = None,
    db_path: str = ".local_autoresearch_cache.db",
    document_cache: Any = None,
    api_key: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    """Execute Stage 2 Multi-Regime Expansion on promising candidates."""
    logger.info(f"🚀 EXECUTING STAGE 2 MULTI-REGIME EXPANSION: evaluating {len(expansion_weeks)} additional weeks...")

    stage2_metrics, stage2_results, stage2_lessons = await evaluate_curriculum_batch(
        curriculum_weeks=expansion_weeks,
        ingestion_prompt=ingestion_prompt,
        criteria=criteria,
        strata_url=strata_url,
        laya_url=laya_url or strata_url,
        db_path=db_path,
        document_cache=document_cache,
        api_key=api_key,
        run_id=f"{run_id}_stage2" if run_id else "stage2",
        run_mini_cycles=True,
        early_prune=config.early_prune_stage2,
    )

    combined_results = list(stage1_results) + list(stage2_results)
    cumulative_metrics = calculate_metrics(combined_results)

    traded_results = [r for r in combined_results if r.get("is_traded", True)]
    total_traded = len(traded_results)
    total_wins = sum(1 for r in traded_results if r.get("is_correct") is True)

    sig = calculate_binomial_significance(
        wins=total_wins,
        total=total_traded,
        null_prob=0.5,
        alpha=config.significance_alpha,
    )

    is_early_pruned = stage2_metrics.get("early_pruned", False)
    cumulative_wr = (total_wins / total_traded) if total_traded > 0 else 0.0

    passed = (not is_early_pruned) and sig["is_significant"] and (cumulative_wr >= config.promising_win_rate)

    status_tag = "✅ STATISTICALLY SIGNIFICANT" if passed else "❌ STAGE 2 FAILED"
    logger.info(
        f"{status_tag}: Cumulative N={total_traded} | Wins: {total_wins}/{total_traded} ({sig['win_rate_pct']}%) | "
        f"p-value: {sig['p_value']:.4f} (alpha={config.significance_alpha}) | Z-score: {sig['z_score']:+.2f}"
    )

    return {
        "escalation_evaluated": True,
        "passed": passed,
        "stage2_metrics": stage2_metrics,
        "cumulative_metrics": cumulative_metrics,
        "significance": sig,
        "combined_results": combined_results,
        "stage2_lessons": stage2_lessons,
    }
