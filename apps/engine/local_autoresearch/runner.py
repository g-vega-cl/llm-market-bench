"""Top-level Orchestrator CLI for Local Autoresearch (Qwen via Strata + Jev on OpenRouter)."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

# Ensure apps/engine root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import logger
from core.db import get_supabase_client
from core.llm.daily_predictor_prompts import format_jev_curated_prompt_content
from local_autoresearch.cache_builder import (
    DEFAULT_CACHE_DB,
    build_cache_from_raw_db,
    build_cache_from_supabase,
    load_cached_weeks,
)
from local_autoresearch.historical_downloader import (
    DEFAULT_PROXIES,
    DEFAULT_RAW_DB,
    HistoricalDownloader,
)
from local_autoresearch.jev_evaluator import (
    evaluate_vault,
    evaluate_weekly_kfold,
    split_weekly_vault,
)
from local_autoresearch.local_store import (
    DEFAULT_LOCAL_DB,
    format_memories_for_prompt,
    get_active_baseline,
    get_recent_memories,
    save_local_experiment,
    save_local_memory,
)
from local_autoresearch.manifest import (
    DataManifest,
    JevCriteriaConfig,
)
from local_autoresearch.reporting import (
    render_terminal_dashboard,
    update_dashboard_artifact,
)
from local_autoresearch.strata_client import (
    DEFAULT_STRATA_URL,
    generate_mutation_with_strata,
    is_strata_available,
)

DEFAULT_ARTIFACT_PATH = (
    "/home/cv/.gemini/antigravity-cli/brain/91f7fa65-7a3b-4e8d-b3b0-2f054a18670d/local_autoresearch_dashboard.md"
)

CLEAN_SHEET_INITIAL_CRITERIA = JevCriteriaConfig(
    criteria_up="Close price >= Open price. Predict UP if SPY will close HIGHER at 4:00 PM ET compared to 9:30 AM ET Open.",
    criteria_down="Close price < Open price. Predict DOWN if SPY will close LOWER at 4:00 PM ET compared to 9:30 AM ET Open.",
    min_confidence=50.0,
)

SEED_ARCHETYPES: dict[str, tuple[JevCriteriaConfig, DataManifest, str]] = {
    "clean-sheet": (
        CLEAN_SHEET_INITIAL_CRITERIA,
        DataManifest(),
        "Clean sheet start from 0 (bare format blocks, no trading heuristics).",
    ),
    "mean-reversion": (
        JevCriteriaConfig(
            criteria_up="Pre-market: SPY overnight gap is strongly negative (<= -0.40%), but 10Y yields are flat/falling and pre-market selling volume slows into 9:15 ET, indicating high probability of an opening gap fill rally.",
            criteria_down="Pre-market: SPY overnight gap is strongly positive (>= +0.40%), but QQQ/IWM breadth fails to confirm and prior session closed below VWAP, indicating an exhausted gap to be faded.",
            min_confidence=52.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "IWM", "TLT"],
            include_options_derivatives=True,
            include_intraday_profile=True,
        ),
        "Mean-reversion archetype: Fade unconfirmed gap extremes and trade opening gap fills.",
    ),
    "macro-rates": (
        JevCriteriaConfig(
            criteria_up="Pre-market: 10Y Treasury yield (TLT positive / yields falling) and 8:30 AM economic calendar prints show growth resilience without inflation surprise. SPY and QQQ pre-market gaps are positive.",
            criteria_down="Pre-market: 10Y Treasury yield surges (TLT negative / yields spiking) or 8:30 AM economic data sparks rate anxiety. SPY and QQQ pre-market gaps are negative.",
            min_confidence=55.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "TLT", "IEF", "GLD"],
            include_economic_calendar=True,
            include_options_derivatives=True,
            include_intraday_profile=False,
        ),
        "Macro-rates archetype: Interest rate shifts and 8:30 AM economic prints drive risk-on/risk-off regimes.",
    ),
    "momentum-breadth": (
        JevCriteriaConfig(
            criteria_up="Pre-market: SPY and QQQ overnight gaps are both positive (>= +0.25%), small-cap IWM confirms positive breadth, and prior session closed above VWAP with positive CLV.",
            criteria_down="Pre-market: SPY and QQQ overnight gaps are both negative (<= -0.25%), small-cap IWM confirms negative breadth, and prior session closed below VWAP with negative CLV.",
            min_confidence=55.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "IWM", "DIA"],
            include_intraday_profile=True,
            include_options_derivatives=True,
        ),
        "Momentum-breadth archetype: Pre-market Gap & Go confirmed by tech and small-cap breadth.",
    ),
    "volatility-skew": (
        JevCriteriaConfig(
            criteria_up="Pre-market: Options put/call volume distribution shows heavy call skew or dealer short gamma exhaustion, SPY holds pre-market support, and QQQ breadth confirms positive risk posture.",
            criteria_down="Pre-market: Options put volume surges with heavy downside put positioning, put/call skew spikes into pre-market, and SPY trades below prior session VWAP.",
            min_confidence=56.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "IWM"],
            include_options_derivatives=True,
            include_intraday_profile=True,
        ),
        "Volatility-skew archetype: Options market implied volatility and put/call positioning drive directional expansion.",
    ),
    "opening-drive": (
        JevCriteriaConfig(
            criteria_up="Pre-market: Prior session closed with strong positive CLV (> 0.50) above VWAP, overnight inventory is net long without exhaustion, and pre-market price holds above yesterday's high.",
            criteria_down="Pre-market: Prior session closed with strong negative CLV (< -0.50) below VWAP, overnight inventory is net short, and pre-market price breaks below yesterday's low.",
            min_confidence=58.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "DIA"],
            include_intraday_profile=True,
        ),
        "Opening-drive archetype: Institutional auction dynamics, prior session CLV, and VWAP value migration.",
    ),
    "cross-asset-flight": (
        JevCriteriaConfig(
            criteria_up="Pre-market: Safe-haven assets TLT and GLD are flat or retreating, Treasury yields are stable, and equities SPY/QQQ show orderly risk-on capital inflows.",
            criteria_down="Pre-market: Clear safe-haven flight into Gold (GLD positive) or Treasuries (TLT surging / yields collapsing) reflecting macro panic; equities SPY/QQQ gap down.",
            min_confidence=57.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "TLT", "GLD", "IEF"],
            include_economic_calendar=True,
        ),
        "Cross-asset-flight archetype: Capital rotation between equities, Treasuries, and Gold signals risk regimes.",
    ),
    "trend-exhaustion": (
        JevCriteriaConfig(
            criteria_up="Pre-market: Prior 2 sessions were heavily negative, SPY overnight gap is small or stabilizing, 10Y yields pause, and options skew indicates short-covering squeeze probability.",
            criteria_down="Pre-market: Prior 2 sessions were parabolic extended rallies, overnight gap opens flat or exhausted, and small-cap IWM fails to confirm, indicating mean-reversion pullback.",
            min_confidence=54.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_options_derivatives=True,
            include_macro_proxies=["QQQ", "IWM"],
            include_intraday_profile=True,
        ),
        "Trend-exhaustion archetype: Identify multi-day directional momentum exhaustion and mean-reversion turning points.",
    ),
    "selective-catalyst": (
        JevCriteriaConfig(
            criteria_up="Pre-market: 8:30 AM economic calendar reports growth resilience (positive surprise) without inflationary pressure, Treasury yields are well-behaved, and SPY pre-market reaction is positive. Trade UP only on clear macro catalyst; otherwise route NO_TRADE.",
            criteria_down="Pre-market: 8:30 AM economic calendar reports stagflationary or negative growth surprise, yields spike or plunge unexpectedly, and SPY reacts negatively. Trade DOWN only on clear macro catalyst; otherwise route NO_TRADE.",
            min_confidence=65.0,
        ),
        DataManifest(
            include_synthetic_newsletter=True,
            include_economic_calendar=True,
            include_macro_proxies=["QQQ", "TLT"],
            include_options_derivatives=True,
        ),
        "Selective-catalyst archetype: Trade strictly on high-impact macroeconomic data releases with aggressive confidence gating.",
    ),
    "contrarian-sentiment": (
        JevCriteriaConfig(
            criteria_up="Pre-market: Morning financial newsletters express pervasive retail pessimism and downside panic, but technical pre-market price action on SPY holds above key support levels, indicating contrarian long setup.",
            criteria_down="Pre-market: Morning financial newsletters display universal retail euphoria and complacency, while pre-market breadth on QQQ/IWM begins diverging lower, indicating a bull-trap fade.",
            min_confidence=55.0,
        ),
        DataManifest(
            selected_newsletters=["Sherwood News", "Chartr", "Exec Sum"],
            include_synthetic_newsletter=True,
            include_macro_proxies=["QQQ", "IWM"],
            include_intraday_profile=True,
        ),
        "Contrarian-sentiment archetype: Fade retail newsletter consensus extremes when pre-market tape diverges.",
    ),
}


async def run_local_autoresearch_loop(
    iterations: int = 5,
    cache_db: str = DEFAULT_CACHE_DB,
    local_db: str = DEFAULT_LOCAL_DB,
    strata_url: str = DEFAULT_STRATA_URL,
    promote_best: bool = False,
    seed: int = 42,
    max_concurrency: int = 10,
    artifact_path: str = DEFAULT_ARTIFACT_PATH,
    calibrate_baseline: bool = False,
    seed_archetype: str | None = None,
) -> dict[str, Any]:
    """Execute the autonomous local prompt & manifest improvement loop."""
    logger.info(f"=== Starting Local Autoresearch: {iterations} iterations ===")

    # 1. Load cached weekly blocks and partition Locked Vault
    weeks_data = load_cached_weeks(cache_db)
    if not weeks_data:
        raise RuntimeError(
            f"No cached trading days found in {cache_db}. Run with --init-cache first to populate from Supabase."
        )

    active_weeks_data, vault_weeks_data = split_weekly_vault(weeks_data, vault_ratio=0.20, seed=seed)
    total_days = sum(len(days) for days in weeks_data.values())
    active_days = sum(len(days) for days in active_weeks_data.values())
    vault_days = sum(len(days) for days in vault_weeks_data.values())
    logger.info(
        f"Loaded {len(weeks_data)} weekly blocks ({total_days} total trading days). "
        f"Partitioned into {len(active_weeks_data)} Active Optimization Weeks ({active_days} days) "
        f"and {len(vault_weeks_data)} Locked Vault Weeks ({vault_days} days)."
    )

    history: list[dict[str, Any]] = []

    # 2. Check or initialize baseline in local_store
    baseline = get_active_baseline(local_db)
    baseline_vault_score = 0.0

    if seed_archetype:
        if seed_archetype not in SEED_ARCHETYPES:
            raise ValueError(f"Unknown seed archetype: {seed_archetype}. Must be one of {list(SEED_ARCHETYPES.keys())}")
        crit, man, hyp = SEED_ARCHETYPES[seed_archetype]
        logger.info(f"Initializing baseline from seed archetype [{seed_archetype}]: {hyp}")
        seed_eval = await evaluate_weekly_kfold(
            weekly_data=active_weeks_data,
            criteria=crit,
            manifest=man,
            seed=seed,
            max_concurrency=max_concurrency,
        )
        if vault_weeks_data:
            seed_vault = await evaluate_vault(
                vault_data=vault_weeks_data,
                criteria=crit,
                manifest=man,
                max_concurrency=max_concurrency,
            )
            baseline_vault_score = seed_vault["score"]
            logger.info(f"Initial Locked Vault Score: {baseline_vault_score:.2f}")

        base_tag = f"seed-{seed_archetype}-{uuid.uuid4().hex[:6]}"
        save_local_experiment(
            variant_tag=base_tag,
            criteria=crit,
            manifest=man,
            train_score=seed_eval["train_metrics"]["score"],
            test_score=seed_eval["test_metrics"]["score"],
            overfit_penalty=seed_eval["overfit_penalty"],
            effective_score=seed_eval["effective_score"],
            is_baseline_beat=True,
            status="baseline",
            hypothesis=hyp,
            db_path=local_db,
        )
        baseline = get_active_baseline(local_db)
        history.append(
            {
                "iteration": 0,
                "variant_tag": base_tag,
                "train_score": seed_eval["train_metrics"]["score"],
                "test_score": seed_eval["test_metrics"]["score"],
                "overfit_penalty": seed_eval["overfit_penalty"],
                "effective_score": seed_eval["effective_score"],
                "vault_score": baseline_vault_score if vault_weeks_data else None,
                "is_baseline_beat": True,
                "hypothesis": hyp,
            }
        )
    elif not baseline:
        logger.info("Starting from 0 (clean sheet): evaluating bare format blocks to establish baseline...")
        base_manifest = DataManifest()
        seed_eval = await evaluate_weekly_kfold(
            weekly_data=active_weeks_data,
            criteria=CLEAN_SHEET_INITIAL_CRITERIA,
            manifest=base_manifest,
            seed=seed,
            max_concurrency=max_concurrency,
        )
        if vault_weeks_data:
            seed_vault = await evaluate_vault(
                vault_data=vault_weeks_data,
                criteria=CLEAN_SHEET_INITIAL_CRITERIA,
                manifest=base_manifest,
                max_concurrency=max_concurrency,
            )
            baseline_vault_score = seed_vault["score"]
            logger.info(f"Initial Locked Vault Score: {baseline_vault_score:.2f}")

        base_tag = f"clean-start-{uuid.uuid4().hex[:6]}"
        save_local_experiment(
            variant_tag=base_tag,
            criteria=CLEAN_SHEET_INITIAL_CRITERIA,
            manifest=base_manifest,
            train_score=seed_eval["train_metrics"]["score"],
            test_score=seed_eval["test_metrics"]["score"],
            overfit_penalty=seed_eval["overfit_penalty"],
            effective_score=seed_eval["effective_score"],
            is_baseline_beat=True,
            status="baseline",
            hypothesis="Clean sheet start from 0 (bare format blocks, no trading heuristics).",
            db_path=local_db,
        )
        baseline = get_active_baseline(local_db)
        history.append(
            {
                "iteration": 0,
                "variant_tag": base_tag,
                "train_score": seed_eval["train_metrics"]["score"],
                "test_score": seed_eval["test_metrics"]["score"],
                "overfit_penalty": seed_eval["overfit_penalty"],
                "effective_score": seed_eval["effective_score"],
                "vault_score": baseline_vault_score if vault_weeks_data else None,
                "is_baseline_beat": True,
                "hypothesis": "Clean sheet start from 0",
            }
        )
    elif baseline and calibrate_baseline:
        logger.info(f"Calibrating active baseline [{baseline['variant_tag']}] dynamically on current dataset...")
        curr_crit = JevCriteriaConfig(
            criteria_up=baseline["criteria_up"],
            criteria_down=baseline["criteria_down"],
            min_confidence=baseline["min_confidence"],
        )
        curr_man = DataManifest(**baseline["manifest"])
        cal_eval = await evaluate_weekly_kfold(
            weekly_data=active_weeks_data,
            criteria=curr_crit,
            manifest=curr_man,
            seed=seed,
            max_concurrency=max_concurrency,
        )
        if vault_weeks_data:
            seed_vault = await evaluate_vault(
                vault_data=vault_weeks_data,
                criteria=curr_crit,
                manifest=curr_man,
                max_concurrency=max_concurrency,
            )
            baseline_vault_score = seed_vault["score"]

        save_local_experiment(
            variant_tag=baseline["variant_tag"],
            criteria=curr_crit,
            manifest=curr_man,
            train_score=cal_eval["train_metrics"]["score"],
            test_score=cal_eval["test_metrics"]["score"],
            overfit_penalty=cal_eval["overfit_penalty"],
            effective_score=cal_eval["effective_score"],
            is_baseline_beat=True,
            status="baseline",
            hypothesis=baseline.get("hypothesis", "Calibrated baseline"),
            db_path=local_db,
        )
        baseline = get_active_baseline(local_db)
        history.append(
            {
                "iteration": 0,
                "variant_tag": baseline["variant_tag"],
                "train_score": cal_eval["train_metrics"]["score"],
                "test_score": cal_eval["test_metrics"]["score"],
                "overfit_penalty": cal_eval["overfit_penalty"],
                "effective_score": cal_eval["effective_score"],
                "vault_score": baseline_vault_score if vault_weeks_data else None,
                "is_baseline_beat": True,
                "hypothesis": baseline.get("hypothesis", "Calibrated baseline"),
            }
        )
    elif vault_weeks_data:
        curr_crit = JevCriteriaConfig(
            criteria_up=baseline["criteria_up"],
            criteria_down=baseline["criteria_down"],
            min_confidence=baseline["min_confidence"],
        )
        curr_man = DataManifest(**baseline["manifest"])
        seed_vault = await evaluate_vault(
            vault_data=vault_weeks_data,
            criteria=curr_crit,
            manifest=curr_man,
            max_concurrency=max_concurrency,
        )
        baseline_vault_score = seed_vault["score"]

    assert baseline is not None
    current_criteria = JevCriteriaConfig(
        criteria_up=baseline["criteria_up"],
        criteria_down=baseline["criteria_down"],
        min_confidence=baseline["min_confidence"],
    )
    current_manifest = DataManifest(**baseline["manifest"])
    baseline_score = float(baseline.get("effective_score", 0.0))
    current_tag = baseline["variant_tag"]

    if not history:
        history.append(
            {
                "iteration": 0,
                "variant_tag": current_tag,
                "train_score": baseline.get("train_score", 0.0),
                "test_score": baseline.get("test_score", 0.0),
                "overfit_penalty": baseline.get("overfit_penalty", 0.0),
                "effective_score": baseline_score,
                "is_baseline_beat": True,
                "hypothesis": baseline.get("hypothesis", "Active baseline"),
            }
        )

    logger.info(f"Active baseline [{current_tag}]: Canonical Ratchet Score = {baseline_score:.2f}")

    # 3. Execution Loop
    for it in range(1, iterations + 1):
        logger.info(f"\n--- Iteration {it}/{iterations} ---")

        # Gather past local memories
        recent_mems = get_recent_memories(limit=5, db_path=local_db)
        memories_text = format_memories_for_prompt(recent_mems)

        # Query local Qwen via Strata for next mutation
        logger.info("Consulting Local Qwen (Strata) for criteria & manifest mutation...")
        try:
            mutation = await generate_mutation_with_strata(
                baseline_criteria=current_criteria,
                baseline_manifest=current_manifest,
                baseline_score=baseline_score,
                train_score=baseline.get("train_score", 0.0),
                test_score=baseline.get("test_score", 0.0),
                memories_context=memories_text,
                base_url=strata_url,
            )
        except Exception as e:
            logger.error(f"Strata mutation failed on iteration {it}: {e}")
            continue

        cand_tag = f"qwen-jev-{uuid.uuid4().hex[:6]}"
        logger.info(f"Proposed mutation [{cand_tag}]: {mutation.hypothesis}")

        # Evaluate candidate across active weekly blocks using non-chronological K-Fold
        logger.info(f"Simulating Jev decisions across {len(active_weeks_data)} active weeks in parallel...")
        eval_res = await evaluate_weekly_kfold(
            weekly_data=active_weeks_data,
            criteria=mutation.criteria,
            manifest=mutation.manifest,
            seed=seed + it,
            max_concurrency=max_concurrency,
        )

        train_score = eval_res["train_metrics"]["score"]
        test_score = eval_res["test_metrics"]["score"]
        overfit_penalty = eval_res["overfit_penalty"]
        eff_score = eval_res["effective_score"]

        is_winner = eff_score > baseline_score
        cand_vault_score = None
        vault_overfit = False

        if is_winner and vault_weeks_data:
            logger.info("Evaluating candidate on unseen Locked Vault to check generalization...")
            vault_res = await evaluate_vault(
                vault_data=vault_weeks_data,
                criteria=mutation.criteria,
                manifest=mutation.manifest,
                max_concurrency=max_concurrency,
            )
            cand_vault_score = vault_res["score"]
            logger.info(
                f"Locked Vault Evaluation [{cand_tag}]: Vault Score={cand_vault_score:.2f} "
                f"(Baseline Vault={baseline_vault_score:.2f}, Traded WR={vault_res['traded_win_rate_pct']}%)"
            )
            # Gate check: Vault score must maintain solid generalization
            if cand_vault_score < max(40.0, baseline_vault_score - 10.0):
                logger.warning(
                    f"⚠️ OVERFITTING DETECTED! Candidate beat active pool ({eff_score:.2f} > {baseline_score:.2f}) "
                    f"but collapsed on unseen Locked Vault ({cand_vault_score:.2f} < threshold). Discarding!"
                )
                is_winner = False
                vault_overfit = True
            else:
                logger.info(f"🛡️ Vault check PASSED! Generalizes out-of-sample (Vault Score: {cand_vault_score:.2f}).")
                baseline_vault_score = cand_vault_score

        logger.info(
            f"Scorecard [{cand_tag}]: Train={train_score:.2f} | Test={test_score:.2f} | "
            f"Overfit Penalty={overfit_penalty:.2f} => Effective Score={eff_score:.2f} "
            f"(Baseline={baseline_score:.2f})"
        )

        status_desc = "baseline" if is_winner else ("vault_overfit" if vault_overfit else "discarded")
        if is_winner:
            logger.info(f"🏆 RATCHET BEATEN! New baseline established: {eff_score:.2f} > {baseline_score:.2f}")
            vault_desc = f"Vault: {cand_vault_score:.2f}" if cand_vault_score is not None else "No vault"
            insight = (
                f"Beat baseline ({eff_score:.2f} vs {baseline_score:.2f}, {vault_desc}). "
                f"Traded win rate: {eval_res['test_metrics']['traded_win_rate_pct']}%. "
                f"Selected newsletters: {mutation.manifest.selected_newsletters}"
            )
            baseline_score = eff_score
            current_tag = cand_tag
            current_criteria = mutation.criteria
            current_manifest = mutation.manifest
        else:
            logger.info(f"Discarding mutation (status: {status_desc})")
            insight = (
                f"Collapsed on Locked Vault ({cand_vault_score:.2f}) despite beating active pool."
                if vault_overfit
                else f"Failed to beat active baseline ({eff_score:.2f} <= {baseline_score:.2f}). Overfit penalty: {overfit_penalty:.2f}."
            )

        save_local_experiment(
            variant_tag=cand_tag,
            criteria=mutation.criteria,
            manifest=mutation.manifest,
            parent_tag=current_tag,
            train_score=train_score,
            test_score=test_score,
            overfit_penalty=overfit_penalty,
            effective_score=eff_score,
            is_baseline_beat=is_winner,
            status=status_desc,
            hypothesis=mutation.hypothesis,
            db_path=local_db,
        )
        save_local_memory(
            iteration=it,
            variant_tag=cand_tag,
            hypothesis=mutation.hypothesis,
            insight=insight,
            test_score=test_score,
            is_baseline_beat=is_winner,
            db_path=local_db,
        )

        history.append(
            {
                "iteration": it,
                "variant_tag": cand_tag,
                "train_score": train_score,
                "test_score": test_score,
                "overfit_penalty": overfit_penalty,
                "effective_score": eff_score,
                "vault_score": cand_vault_score,
                "is_baseline_beat": is_winner,
                "status_reason": "vault_overfit" if vault_overfit else ("winner" if is_winner else "discarded"),
                "hypothesis": mutation.hypothesis,
            }
        )

        active_bl = get_active_baseline(local_db) or {}
        weekly_b = eval_res.get("weekly_breakdown")
        dashboard_str = render_terminal_dashboard(history, active_bl, latest_weekly_breakdown=weekly_b)
        print(dashboard_str)
        update_dashboard_artifact(history, active_bl, artifact_path, latest_weekly_breakdown=weekly_b)

    best = get_active_baseline(local_db)
    logger.info(
        f"\n=== Autoresearch Completed. Current Best Baseline: {best['variant_tag']} (Score: {best['effective_score']:.2f}) ==="
    )

    # 4. Optional promotion to Supabase
    if promote_best and best:
        try:
            promote_baseline_to_supabase(local_db=local_db)
        except Exception as e:
            logger.error(f"Failed to promote winning baseline to Supabase: {e}")

    return best or {}


def promote_baseline_to_supabase(
    local_db: str = DEFAULT_LOCAL_DB,
    track_id: str = "jev-local-autoresearched",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Promote the winning local baseline to Supabase strictly under track_id without mutating other tracks."""
    best = get_active_baseline(local_db)
    if not best:
        raise ValueError(f"No active baseline found in {local_db} to promote.")

    criteria = {
        "UP": best["criteria_up"],
        "DOWN": best["criteria_down"],
    }
    min_confidence = float(best.get("min_confidence", 50.0))
    manifest = best.get("manifest", {})
    prompt_content = format_jev_curated_prompt_content(
        criteria=criteria,
        min_confidence=min_confidence,
        manifest=manifest,
    )

    tag = f"daily-pred-qwen-local-{uuid.uuid4().hex[:6]}"
    today = datetime.now(UTC).date()
    record = {
        "variant_tag": tag,
        "prompt_name": "DAILY_PREDICTOR_PROMPT",
        "prompt_content": prompt_content,
        "track_id": track_id,
        "week_start": today.isoformat(),
        "week_end": (today + timedelta(days=7)).isoformat(),
        "status": "active",
        "experiment_type": "baseline",
        "change_description": (
            f"Promoted from local Qwen/Strata autoresearch [{best['variant_tag']}]: "
            f"score={best['effective_score']:.2f}. {best.get('hypothesis', '')}"
        ),
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would promote {best['variant_tag']} to track {track_id}: tag={tag}")
        return record

    client = get_supabase_client()
    # Demote only existing active records for this specific track
    client.table("prompt_experiments").update({"status": "saved"}).eq("prompt_name", "DAILY_PREDICTOR_PROMPT").eq(
        "track_id", track_id
    ).eq("status", "active").execute()

    # Insert new record as active baseline
    client.table("prompt_experiments").insert(record).execute()
    logger.info(f"Successfully promoted winning local baseline to Supabase for track {track_id} as {tag}!")
    return record


async def evaluate_baseline_on_vault(
    local_db: str = DEFAULT_LOCAL_DB,
    vault_cache_db: str = ".regime_vault_cache.db",
    cache_db: str = DEFAULT_CACHE_DB,
    seed: int = 42,
    max_concurrency: int = 10,
) -> dict[str, Any]:
    """Evaluate current active baseline against held-out historical Regime Vault."""
    best = get_active_baseline(local_db)
    if not best:
        raise ValueError(f"No active baseline found in {local_db} to evaluate.")

    vault_weeks: dict[str, list[dict[str, Any]]] = {}
    if os.path.exists(vault_cache_db):
        vault_weeks = load_cached_weeks(vault_cache_db)

    if not vault_weeks and os.path.exists(cache_db):
        all_weeks = load_cached_weeks(cache_db)
        _, vault_weeks = split_weekly_vault(all_weeks, vault_ratio=0.20, seed=seed)

    if not vault_weeks:
        raise ValueError(f"No cached vault weeks found in {vault_cache_db} or partitioned from {cache_db}.")

    criteria = JevCriteriaConfig(
        criteria_up=best["criteria_up"],
        criteria_down=best["criteria_down"],
        min_confidence=float(best.get("min_confidence", 50.0)),
    )
    manifest = DataManifest.model_validate(best.get("manifest", {}))

    eval_result = await evaluate_vault(vault_weeks, criteria, manifest, max_concurrency=max_concurrency)
    print("\n" + "=" * 60)
    print(f"REGIME VAULT EVALUATION REPORT: {best['variant_tag']}")
    print("=" * 60)
    print(f"Vault Score               : {eval_result['score']:.2f} / 100")
    print(f"Traded Win Rate           : {eval_result['traded_win_rate_pct']:.1f}%")
    print(f"Total Days / Traded       : {eval_result['total_days']} / {eval_result['traded_days']}")
    print(f"Confidence Gate (NO_TRADE): {eval_result['no_trade_days']} days gated out")
    print(f"Hypothesis                : {best.get('hypothesis', 'N/A')}")
    print("=" * 60 + "\n")
    return eval_result


async def run_archetype_curriculum(
    archetypes: list[str] | None = None,
    iterations_per_archetype: int = 30,
    cache_db: str = DEFAULT_CACHE_DB,
    local_db: str = DEFAULT_LOCAL_DB,
    strata_url: str = DEFAULT_STRATA_URL,
    artifact_path: str = DEFAULT_ARTIFACT_PATH,
    kill_strata: bool = False,
) -> dict[str, dict[str, Any]]:
    """Execute multiple archetypes sequentially, recording champions, and optionally stopping Strata."""
    if archetypes is None:
        archetypes = [
            "macro-rates",
            "momentum-breadth",
            "volatility-skew",
            "opening-drive",
            "cross-asset-flight",
            "trend-exhaustion",
            "selective-catalyst",
            "contrarian-sentiment",
            "clean-sheet",
        ]

    results: dict[str, dict[str, Any]] = {}
    for idx, arch in enumerate(archetypes):
        logger.info(
            f"\n{'=' * 70}\nSTARTING CURRICULUM BATCH {idx + 1}/{len(archetypes)}: "
            f"ARCHETYPE [{arch}] ({iterations_per_archetype} it)\n{'=' * 70}"
        )
        best = await run_local_autoresearch_loop(
            iterations=iterations_per_archetype,
            cache_db=cache_db,
            local_db=local_db,
            strata_url=strata_url,
            promote_best=False,
            artifact_path=artifact_path,
            seed_archetype=arch,
        )
        if best:
            results[arch] = best
            logger.info(
                f"Batch completed for [{arch}]: Winner={best.get('variant_tag')} "
                f"Score={best.get('effective_score', 0.0):.2f}"
            )

    if kill_strata:
        logger.info("All curriculum batches completed. Terminating Strata daemon...")
        os.system("pkill -f 'server.py.*--engine strata' || fuser -k 8080/tcp 2>/dev/null")

    return results


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Local Autoresearch with Strata and Jev")
    parser.add_argument("--iterations", type=int, default=5, help="Number of research iterations")
    parser.add_argument("--init-cache", action="store_true", help="Materialize cache from Supabase before running")
    parser.add_argument("--limit-cache-days", type=int, default=300, help="Days to pull when initializing cache")
    parser.add_argument("--strata-url", type=str, default=DEFAULT_STRATA_URL, help="Strata local base URL")
    parser.add_argument("--check-strata", action="store_true", help="Probe Strata local server health")
    parser.add_argument("--promote-best", action="store_true", help="Promote highest-scoring variant to Supabase")
    parser.add_argument("--dry-run", action="store_true", help="Dry run for promotion without mutating Supabase")
    parser.add_argument("--reset", action="store_true", help="Reset local database to start fresh from clean sheet")
    parser.add_argument("--cache-db", type=str, default=DEFAULT_CACHE_DB, help="Cache SQLite path")
    parser.add_argument("--local-db", type=str, default=DEFAULT_LOCAL_DB, help="Local DB path")
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for data partition (default None: randomized per run)"
    )
    parser.add_argument("--artifact-path", type=str, default=DEFAULT_ARTIFACT_PATH, help="Path for session artifact")
    # Historical downloader & vault flags
    parser.add_argument("--download-raw", action="store_true", help="Download raw historical data via APIs & IMAP")
    parser.add_argument("--build-historical-cache", action="store_true", help="Compile raw DB into feature cache")
    parser.add_argument("--raw-db", type=str, default=DEFAULT_RAW_DB, help="Raw SQLite DB path")
    parser.add_argument("--symbols", type=str, default=",".join(DEFAULT_PROXIES), help="Symbols to download")
    parser.add_argument("--pm-symbols", type=str, default="SPY,QQQ,IWM", help="Symbols for Polygon 5-min bars")
    parser.add_argument("--start-date", type=str, default="2024-10-01", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, default="2026-10-10", help="End date (YYYY-MM-DD)")
    parser.add_argument("--regime-vault", action="store_true", help="Build cache in Regime Vault mode (omit PM tape)")
    parser.add_argument("--eval-vault", action="store_true", help="Evaluate active baseline on Regime Vault")
    parser.add_argument("--vault-cache-db", type=str, default=".regime_vault_cache.db", help="Vault cache DB path")

    parser.add_argument(
        "--calibrate-baseline",
        action="store_true",
        help="Re-evaluate baseline metrics dynamically on current active dataset",
    )
    parser.add_argument(
        "--seed-archetype",
        type=str,
        choices=list(SEED_ARCHETYPES.keys()),
        default=None,
        help="Initialize tournament from a specific quantitative archetype seed",
    )
    parser.add_argument(
        "--curriculum",
        action="store_true",
        help="Run archetypes sequentially as a multi-batch curriculum",
    )
    parser.add_argument(
        "--archetypes",
        type=str,
        default=None,
        help="Comma-separated list of archetypes for curriculum",
    )
    parser.add_argument(
        "--kill-strata",
        action="store_true",
        help="Terminate Strata daemon upon tournament completion",
    )
    parser.add_argument(
        "--double-ratchet",
        action="store_true",
        help="Run Strata (Qwen) + Laya (ModernBERT-large) double-ratchet tournament",
    )
    parser.add_argument(
        "--laya-url",
        type=str,
        default="http://127.0.0.1:8081/v1/systemone",
        help="Laya decision server endpoint",
    )
    parser.add_argument(
        "--check-laya",
        action="store_true",
        help="Probe Laya local server health",
    )
    parser.add_argument(
        "--max-eval-days",
        type=int,
        default=None,
        help="Limit number of evaluation days for quick testing passes",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        default=True,
        help="Generate fresh daily briefings for every session day on every mutation (no cache reuse, default True)",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        default=False,
        help="Reuse cached daily briefings if available (default False)",
    )
    parser.add_argument(
        "--curriculum-weeks",
        type=int,
        default=None,
        help="Run tournament over an atomic multi-week curriculum (e.g. 5 or 10 weeks) with Friday mini-cycles",
    )
    parser.add_argument(
        "--dry-run-set",
        action="store_true",
        help="Run a single baseline curriculum pass (~50 days) to verify pipeline health without mutations",
    )

    args = parser.parse_args()

    if args.reset and os.path.exists(args.local_db):
        os.remove(args.local_db)
        print(f"Reset {args.local_db} (clean sheet start from 0).")

    if args.check_strata:
        is_up = asyncio.run(is_strata_available(args.strata_url))
        print(f"Strata at {args.strata_url} is {'UP and RESPONDING' if is_up else 'OFFLINE or NOT REACHABLE'}")
        return

    if args.check_laya:
        from local_autoresearch.laya_client import is_laya_available

        health_url = args.laya_url.replace("/v1/systemone", "/health")
        is_up = asyncio.run(is_laya_available(health_url))
        print(f"Laya at {args.laya_url} is {'UP and RESPONDING' if is_up else 'OFFLINE or NOT REACHABLE'}")
        return

    if args.double_ratchet:
        cached_weeks = load_cached_weeks(args.cache_db)

        if args.curriculum_weeks or args.dry_run_set:
            from local_autoresearch.double_ratchet import run_double_ratchet_curriculum_tournament

            num_weeks = args.curriculum_weeks or 10
            its = 0 if args.dry_run_set else args.iterations
            no_cache_flag = not args.use_cache
            print("=" * 60)
            print(f"STARTING DOUBLE-RATCHET CURRICULUM ({num_weeks} WEEKS, {its} ITERATIONS)")
            print(f"Dry-run baseline only: {args.dry_run_set}")
            print(f"Random seed: {args.seed} ({'deterministic' if args.seed is not None else 'randomized per run'})")
            print(f"Fresh newsletter ingestion (no-cache): {no_cache_flag}")
            print("=" * 60)

            summary = asyncio.run(
                run_double_ratchet_curriculum_tournament(
                    all_weeks=cached_weeks,
                    num_curriculum_weeks=num_weeks,
                    iterations=its,
                    strata_url=args.strata_url,
                    laya_url=args.laya_url,
                    seed=args.seed,
                    cache_db_path=args.cache_db,
                    no_cache=no_cache_flag,
                )
            )
            print("=" * 60)
            print("DOUBLE-RATCHET CURRICULUM RUN COMPLETE")
            print(f"Baseline Score: {summary['baseline_score']:.2f}")
            print(f"Champion Score: {summary['champion_score']:.2f}")
            if summary.get("stashed_test_metrics"):
                st_m = summary["stashed_test_metrics"]
                print(
                    f"Stashed Test Score (Unseen {summary.get('stashed_test_weeks_count', 0)} weeks): "
                    f"{st_m['score']:.2f} | Win Rate: {st_m['traded_win_rate_pct']:.1f}% | "
                    f"Traded: {st_m['traded_days']}/{st_m['total_days']}"
                )
            print(f"Total History Steps: {len(summary['history'])}")
            if len(summary["history"]) > 1:
                print("\n" + "=" * 30 + " AUTORESEARCHED PROMPT MUTATIONS " + "=" * 30)
                for h in summary["history"][1:]:
                    print(f"\n[Iteration {h['iteration']} - Accepted: {h['accepted']}]")
                    print(f"Hypothesis: {h.get('hypothesis', 'N/A')}")
                    print(f"Score: {h['score']:.2f} (Win Rate: {h['metrics']['traded_win_rate_pct']:.1f}%)")
                print("\n--- CHAMPION CRITERIA (PROMPT 2) ---")
                print(f"Criteria UP: {summary['champion_criteria']['criteria_up']}")
                print(f"Criteria DOWN: {summary['champion_criteria']['criteria_down']}")
                print(f"Min Confidence: {summary['champion_criteria']['min_confidence']:.1f}%")
                print("\n--- CHAMPION INGESTION PROMPT (PROMPT 1) ---")
                print(summary["champion_ingestion_prompt"].strip())
            print("=" * 60)
            return

        from local_autoresearch.double_ratchet import run_double_ratchet_tournament

        all_days = [day for days in cached_weeks.values() for day in days]
        if args.max_eval_days and len(all_days) > args.max_eval_days:
            all_days = all_days[: args.max_eval_days]

        summary = asyncio.run(
            run_double_ratchet_tournament(
                all_days=all_days,
                iterations=args.iterations,
                strata_url=args.strata_url,
                laya_url=args.laya_url,
                held_out_ratio=0.15,
                seed=args.seed,
                cache_db_path=args.cache_db,
                no_cache=args.no_cache,
            )
        )
        print("=" * 60)
        print("DOUBLE-RATCHET TOURNAMENT COMPLETE")
        print(f"Baseline Score: {summary['baseline_score']:.2f}")
        print(f"Champion Score: {summary['champion_score']:.2f}")
        print(f"Held-Out Score: {summary['held_out_metrics']['score']:.2f}")
        print("=" * 60)
        return

    if args.download_raw:
        syms = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
        pm_syms = [s.strip().upper() for s in args.pm_symbols.split(",") if s.strip()]
        downloader = HistoricalDownloader(db_path=args.raw_db)
        print(f"Starting raw historical download into {args.raw_db} ({args.start_date} to {args.end_date})...")
        eod_c = downloader.download_fmp_eod(syms, args.start_date, args.end_date)
        pm_stats = downloader.download_multi_polygon_bars(pm_syms, args.start_date, args.end_date)
        print(f"Download complete: {eod_c} EOD bars, Polygon 5-min bars: {pm_stats}.")
        if not any(arg.startswith("--iterations") for arg in sys.argv):
            return

    if args.build_historical_cache:
        target_cache = args.vault_cache_db if args.regime_vault else args.cache_db
        cnt = build_cache_from_raw_db(
            raw_db_path=args.raw_db,
            cache_db_path=target_cache,
            start_date=args.start_date,
            end_date=args.end_date,
            is_regime_vault=args.regime_vault,
        )
        print(f"Materialized {cnt} days into {target_cache} (regime_vault={args.regime_vault}).")
        if not any(arg.startswith("--iterations") for arg in sys.argv):
            return

    if args.eval_vault:
        asyncio.run(
            evaluate_baseline_on_vault(
                local_db=args.local_db,
                vault_cache_db=args.vault_cache_db,
                cache_db=args.cache_db,
            )
        )
        return

    if args.init_cache:
        client = get_supabase_client()
        count = asyncio.run(build_cache_from_supabase(client, limit_days=args.limit_cache_days, db_path=args.cache_db))
        print(f"Cache initialization complete: {count} historical days cached in {args.cache_db}.")
        if not any(arg.startswith("--iterations") for arg in sys.argv):
            return

    if args.promote_best and not any(arg.startswith("--iterations") for arg in sys.argv):
        rec = promote_baseline_to_supabase(
            local_db=args.local_db,
            track_id="jev-local-autoresearched",
            dry_run=args.dry_run,
        )
        print(
            f"Promotion {'dry run' if args.dry_run else 'complete'}: {rec['variant_tag']} for track {rec['track_id']}"
        )
        return

    if args.curriculum:
        arch_list = [a.strip() for a in args.archetypes.split(",") if a.strip()] if args.archetypes else None
        asyncio.run(
            run_archetype_curriculum(
                archetypes=arch_list,
                iterations_per_archetype=args.iterations,
                cache_db=args.cache_db,
                local_db=args.local_db,
                strata_url=args.strata_url,
                artifact_path=args.artifact_path,
                kill_strata=args.kill_strata,
            )
        )
        return

    asyncio.run(
        run_local_autoresearch_loop(
            iterations=args.iterations,
            cache_db=args.cache_db,
            local_db=args.local_db,
            strata_url=args.strata_url,
            promote_best=args.promote_best,
            artifact_path=args.artifact_path,
            calibrate_baseline=args.calibrate_baseline,
            seed_archetype=args.seed_archetype,
        )
    )


if __name__ == "__main__":
    main()
