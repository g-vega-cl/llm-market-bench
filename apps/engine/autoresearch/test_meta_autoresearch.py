"""Colocated tests for Monthly Meta-Autoresearcher (Mutation Yield ratchet)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from autoresearch.meta_autoresearch import (
    DEFAULT_META_MUTATION_DIRECTIVES,
    META_PROMPT_NAME,
    META_TRACK_ID,
    MetaAutoresearchResponse,
    compute_block_and_type_leaderboard,
    compute_monthly_mutation_yield,
    format_empirical_meta_leaderboard,
    get_active_meta_directives_sync,
    run_monthly_meta_autoresearch,
    should_run_monthly_meta_autoresearch,
    splice_research_program,
    split_research_program,
)


def _sample_experiments() -> list[dict]:
    """Build hermetic 30-day weekly prompt_experiments across portfolio and daily tracks."""
    return [
        # Baseline seed row (no parent_tag -> excluded from mutation yield denominator)
        {
            "variant_tag": "seed-port-1",
            "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
            "track_id": "track_default",
            "parent_tag": None,
            "status": "saved",
            "experiment_type": "incremental",
            "metrics": {"score": 10.0},
            "research_output": {"selected_prompt_blocks": ["let_winners_run"]},
        },
        # Weekly mutation 1: beat baseline (+4.0 delta)
        {
            "variant_tag": "v-port-w1",
            "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
            "track_id": "track_default",
            "parent_tag": "seed-port-1",
            "status": "baseline",
            "experiment_type": "incremental",
            "metrics": {"score": 14.0},
            "research_output": {
                "selected_prompt_blocks": ["let_winners_run", "macro_regime_routing"],
                "research_insight": "Macro regime routing prevented tech drawdown.",
            },
        },
        # Weekly mutation 2: failed to beat baseline (-6.0 delta)
        {
            "variant_tag": "v-port-w2",
            "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
            "track_id": "track_default",
            "parent_tag": "v-port-w1",
            "status": "discarded",
            "experiment_type": "radical",
            "metrics": {"score": 8.0},
            "research_output": {
                "selected_prompt_blocks": ["catalyst_expiry_timer"],
                "research_insight": "48h expiry exited winners prematurely.",
            },
        },
        # Daily predictor mutation 3: beat baseline (+5.0 delta)
        {
            "variant_tag": "daily-pred-deepseek-w1",
            "prompt_name": "DAILY_PREDICTOR_PROMPT",
            "track_id": "deepseek-v4-flash",
            "parent_tag": "daily-seed-1",
            "status": "baseline",
            "experiment_type": "incremental",
            "metrics": {"score": 65.0, "baseline_score": 60.0},
            "research_output": {
                "selected_prompt_blocks": ["macro_regime_routing"],
                "research_insight": "Four-regime check improved UP recall.",
            },
        },
        # Daily predictor mutation 4: crashed (-15.0 clamped delta)
        {
            "variant_tag": "v-port-w3",
            "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
            "track_id": "track_claude",
            "parent_tag": "v-port-w1",
            "status": "crashed",
            "experiment_type": "radical",
            "metrics": {"score": -10.0},
            "research_output": {
                "selected_prompt_blocks": ["catalyst_expiry_timer"],
            },
        },
    ]


def test_compute_monthly_mutation_yield_math():
    experiments = _sample_experiments()
    metrics = compute_monthly_mutation_yield(experiments)

    # 4 evaluated mutations (seed-port-1 has no parent_tag and is excluded)
    assert metrics["total_evaluated"] == 4
    assert metrics["beat_count"] == 2
    assert metrics["discarded_count"] == 1
    assert metrics["crash_count"] == 1
    assert metrics["beat_rate_pct"] == 50.0
    assert metrics["non_crash_rate_pct"] == 75.0

    # Deltas: +4.0, -6.0, +5.0, -15.0 (clamped from -24.0) -> sum = -12.0, mean = -3.0
    assert pytest.approx(metrics["mean_clamped_delta"], 0.01) == -3.0
    # Normalized delta score: ((-3.0 + 15.0) / 30.0) * 100 = 40.0
    # Yield = 0.50 * 50.0 + 0.35 * 40.0 + 0.15 * 75.0 = 25.0 + 14.0 + 11.25 = 50.25
    assert pytest.approx(metrics["score"], 0.01) == 50.25


def test_compute_monthly_mutation_yield_empty():
    metrics = compute_monthly_mutation_yield([])
    assert metrics["total_evaluated"] == 0
    assert metrics["score"] == 0.0
    assert metrics["beat_rate_pct"] == 0.0


def test_compute_block_and_type_leaderboard():
    experiments = _sample_experiments()
    board = compute_block_and_type_leaderboard(experiments)

    blocks = {b["block_id"]: b for b in board["blocks"]}
    assert "macro_regime_routing" in blocks
    assert blocks["macro_regime_routing"]["uses"] == 2
    assert blocks["macro_regime_routing"]["beats"] == 2
    assert blocks["macro_regime_routing"]["beat_rate_pct"] == 100.0

    assert "catalyst_expiry_timer" in blocks
    assert blocks["catalyst_expiry_timer"]["uses"] == 2
    assert blocks["catalyst_expiry_timer"]["beats"] == 0
    assert blocks["catalyst_expiry_timer"]["beat_rate_pct"] == 0.0

    exp_types = {t["experiment_type"]: t for t in board["experiment_types"]}
    assert exp_types["incremental"]["uses"] == 2
    assert exp_types["incremental"]["beat_rate_pct"] == 100.0
    assert exp_types["radical"]["uses"] == 2
    assert exp_types["radical"]["beat_rate_pct"] == 0.0

    md = format_empirical_meta_leaderboard(board)
    assert "macro_regime_routing" in md
    assert "catalyst_expiry_timer" in md
    assert "100.0%" in md


def test_split_research_program_preserves_frozen_toolbox_and_schema():
    from autoresearch.researcher import _load_research_program

    raw_program = _load_research_program()
    header, mutable, footer = split_research_program(raw_program)

    assert "# Auto-Research Prompt Improver" in header
    assert "## How to Improve the Prompt" in mutable
    assert "## Toolbox: Available Trading Agent Tools" in footer
    assert "## Output Format" in footer
    assert "get_portfolio_ledger" in footer


def test_should_run_monthly_meta_autoresearch_gate():
    # Day 3 of month with no prior run this month -> True
    assert should_run_monthly_meta_autoresearch(date(2026, 11, 1), []) is True
    # Day 15 of month -> False unless forced
    assert should_run_monthly_meta_autoresearch(date(2026, 11, 15), []) is False
    assert should_run_monthly_meta_autoresearch(date(2026, 11, 15), [], force=True) is True
    # Day 5 of month, but already ran in 2026-11 -> False
    existing = [{"week_start": "2026-11-01"}]
    assert should_run_monthly_meta_autoresearch(date(2026, 11, 5), existing) is False


class _MetaPromptExperimentsBuilder:
    def __init__(
        self, meta_variants: list[dict], experiments: list[dict], inserted_rows: list[dict], updated_calls: list
    ):
        self._filters: dict = {}
        self._op = "select"
        self._payload = None
        self._meta_variants = meta_variants
        self._experiments = experiments
        self._inserted_rows = inserted_rows
        self._updated_calls = updated_calls

    def select(self, *_args, **_kwargs):
        self._op = "select"
        return self

    def update(self, payload):
        self._op = "update"
        self._payload = payload
        return self

    def insert(self, payload):
        self._op = "insert"
        self._payload = payload
        self._inserted_rows.append(payload)
        return self

    def eq(self, k, v):
        self._filters[k] = v
        return self

    def in_(self, k, v):
        self._filters[k] = v
        return self

    def __getattr__(self, name):
        if name in ("gte", "lte", "order", "limit"):
            return lambda *_a, **_kw: self
        raise AttributeError(name)

    def execute(self):
        res = MagicMock()
        if self._op == "insert":
            res.data = [self._payload]
            return res
        if self._op == "update":
            self._updated_calls.append((self._payload, str(self._filters)))
            res.data = []
            return res
        if self._filters.get("prompt_name") == META_PROMPT_NAME:
            status_filter = self._filters.get("status")
            if status_filter == "active":
                res.data = [v for v in self._meta_variants if v["status"] == "active"]
            else:
                res.data = list(self._meta_variants)
        else:
            res.data = list(self._experiments)
        return res


@pytest.mark.asyncio
async def test_run_monthly_meta_autoresearch_ratchet_and_mutation():
    """Verify monthly meta-autoresearch scores Mutation Yield, applies ratchet, and saves new active meta-program."""
    experiments = _sample_experiments()

    # Existing active meta-program has lower score than baseline -> should revert to baseline first
    meta_variants = [
        {
            "variant_tag": "meta-base-v1",
            "prompt_name": META_PROMPT_NAME,
            "track_id": META_TRACK_ID,
            "status": "baseline",
            "week_start": "2026-09-01",
            "prompt_content": "## How to Improve the Prompt\n- Baseline meta rule.",
            "metrics": {"score": 65.0},
            "research_output": {"selected_tools": ["meta_audit"]},
        },
        {
            "variant_tag": "meta-active-v2",
            "prompt_name": META_PROMPT_NAME,
            "track_id": META_TRACK_ID,
            "status": "active",
            "week_start": "2026-10-04",
            "prompt_content": "## How to Improve the Prompt\n- Regressed meta rule.",
            "metrics": {},
            "research_output": {"selected_tools": ["meta_audit"]},
        },
    ]

    inserted_rows: list[dict] = []
    updated_calls: list[tuple[dict, str]] = []

    mock_client = MagicMock()

    def _table_router(table_name: str):
        if table_name == "prompt_experiments":
            return _MetaPromptExperimentsBuilder(meta_variants, experiments, inserted_rows, updated_calls)
        return MagicMock()

    mock_client.table.side_effect = _table_router

    mock_llm = MagicMock()
    mock_llm.chat.completions.create = AsyncMock(
        return_value=MetaAutoresearchResponse(
            new_meta_directives=(
                "## How to Improve the Prompt\n"
                "- Prioritize `macro_regime_routing` (100% beat rate).\n"
                "- Avoid `catalyst_expiry_timer` (0% beat rate) and one-sided whiplash edits."
            ),
            change_description="Deprecate catalyst_expiry_timer and enforce anti-whiplash symmetry.",
            research_insight="Incremental mutations with macro_regime_routing outperformed radical resets 100% to 0%.",
            confidence=85,
        )
    )

    result = await run_monthly_meta_autoresearch(
        client=mock_client,
        meta_llm_client=mock_llm,
        today=date(2026, 11, 1),
        dry_run=False,
        force=True,
    )

    assert result is not None
    assert result["ratchet_action"] == "reverted_to_baseline"
    assert result["parent_tag"] == "meta-base-v1"
    assert len(inserted_rows) == 1
    new_row = inserted_rows[0]
    assert new_row["prompt_name"] == META_PROMPT_NAME
    assert new_row["track_id"] == META_TRACK_ID
    assert new_row["parent_tag"] == "meta-base-v1"
    assert "macro_regime_routing" in new_row["prompt_content"]


def test_get_active_meta_directives_sync_fallback():
    mock_client = MagicMock()
    mock_client.table.side_effect = RuntimeError("DB offline")
    directives = get_active_meta_directives_sync(client=mock_client)
    assert "Anti-Whiplash Symmetry" in directives or DEFAULT_META_MUTATION_DIRECTIVES in directives


@pytest.mark.asyncio
async def test_portfolio_researcher_and_daily_autoresearch_inject_meta_directives(monkeypatch):
    """Verify both Portfolio run_research and Daily generate_new_daily_prompt consume monthly meta-directives."""
    custom_directive = "=== MONTHLY META DIRECTIVE: FAVOR MACRO REGIME ROUTING ==="
    monkeypatch.setattr(
        "autoresearch.meta_autoresearch.get_active_meta_directives_sync",
        lambda *_a, **_kw: custom_directive,
    )

    # 1. Check Daily Predictor generate_new_daily_prompt
    from tasks.daily_autoresearch import DailyMetaPromptResponse, generate_new_daily_prompt

    captured_daily_msgs = []
    mock_daily_meta = MagicMock()

    async def _fake_daily_create(**kwargs):
        captured_daily_msgs.extend(kwargs.get("messages", []))
        return DailyMetaPromptResponse(new_prompt="New strategy body", research_insight="Insight")

    mock_daily_meta.chat.completions.create = _fake_daily_create
    await generate_new_daily_prompt(
        old_prompt="Old strategy",
        baseline_score=55.0,
        predictions=[],
        macro_context={},
        meta_researcher=mock_daily_meta,
    )
    assert any(custom_directive in m["content"] for m in captured_daily_msgs)

    # 2. Check Portfolio researcher.run_research
    from autoresearch import researcher
    from autoresearch.researcher import PromptResearchResult

    captured_port_msgs = []
    mock_port_client = MagicMock()

    async def _fake_port_create(**kwargs):
        captured_port_msgs.extend(kwargs.get("messages", []))
        return PromptResearchResult(
            new_prompt_text="Modified portfolio strategy",
            selected_tools=["get_portfolio_ledger"],
            selected_prompt_blocks=["macro_regime_routing"],
            change_description="Added macro routing",
            experiment_type="incremental",
            research_reasoning="Empirical block win rate",
            confidence=80,
            research_insight="Macro routing beat baseline",
        )

    mock_port_client.chat.completions.create = _fake_port_create
    monkeypatch.setattr(
        researcher,
        "_get_client_and_provider_for_model",
        lambda _m: (mock_port_client, "deepseek"),
    )
    monkeypatch.setattr(
        "autoresearch.tools.query_trade_postmortems",
        AsyncMock(return_value=""),
    )

    await researcher.run_research("Weekly report", track_id="track_default")
    assert any(custom_directive in m["content"] for m in captured_port_msgs if m["role"] == "system")


def test_compute_block_and_type_leaderboard_bayesian_shrinkage():
    """Verify high-sample proven blocks outrank low-sample lucky flukes via Bayesian shrinkage."""
    experiments = [
        # Baseline seed
        {
            "variant_tag": "seed",
            "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
            "track_id": "track_default",
            "parent_tag": None,
            "status": "saved",
            "experiment_type": "incremental",
            "metrics": {"score": 10.0},
            "research_output": {},
        },
        # Block Rare: 1 use, 1 beat (100% raw)
        {
            "variant_tag": "rare-1",
            "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
            "track_id": "track_default",
            "parent_tag": "seed",
            "status": "baseline",
            "experiment_type": "incremental",
            "metrics": {"score": 15.0},
            "research_output": {"selected_prompt_blocks": ["block_rare"]},
        },
    ]
    # Block Proven: 10 uses, 8 beats (80% raw)
    for i in range(10):
        is_beat = i < 8
        experiments.append(
            {
                "variant_tag": f"proven-{i}",
                "prompt_name": "CORE_ANALYSIS_SYSTEM_PROMPT",
                "track_id": "track_default",
                "parent_tag": "seed",
                "status": "baseline" if is_beat else "discarded",
                "experiment_type": "incremental",
                "metrics": {"score": 15.0 if is_beat else 8.0},
                "research_output": {"selected_prompt_blocks": ["block_proven"]},
            }
        )

    board = compute_block_and_type_leaderboard(experiments)
    blocks = board["blocks"]

    # Assert block_proven ranks FIRST over block_rare
    assert len(blocks) == 2
    assert blocks[0]["block_id"] == "block_proven"
    assert blocks[0]["uses"] == 10
    assert blocks[0]["beat_rate_pct"] == 80.0
    # Shrunk rate: 50.0 + (80.0 - 50.0) * (10 / 14) = 71.4%
    assert pytest.approx(blocks[0]["shrunk_beat_rate_pct"], 0.1) == 71.4

    assert blocks[1]["block_id"] == "block_rare"
    assert blocks[1]["uses"] == 1
    assert blocks[1]["beat_rate_pct"] == 100.0
    # Shrunk rate: 50.0 + (100.0 - 50.0) * (1 / 5) = 60.0%
    assert pytest.approx(blocks[1]["shrunk_beat_rate_pct"], 0.1) == 60.0


def test_splice_research_program():
    """Verify splice_research_program replaces ## How to Improve the Prompt cleanly."""
    from autoresearch.researcher import _load_research_program

    raw_program = _load_research_program()
    custom_directives = "## How to Improve the Prompt\n- **Rule 1**: Test strictly.\n- **Rule 2**: No whiplash."
    spliced = splice_research_program(raw_program, custom_directives)

    # Must contain custom directives
    assert "- **Rule 1**: Test strictly." in spliced
    assert "- **Rule 2**: No whiplash." in spliced
    # Must preserve header and toolbox footer
    assert "# Auto-Research Prompt Improver" in spliced
    assert "## Toolbox: Available Trading Agent Tools" in spliced
    # Must NOT have duplicate "## How to Improve the Prompt"
    assert spliced.count("## How to Improve the Prompt") == 1


def test_get_active_meta_directives_sync_ttl_cache():
    """Verify get_active_meta_directives_sync caches result and avoids repeated DB hits."""
    from autoresearch.meta_autoresearch import clear_meta_directives_cache

    clear_meta_directives_cache()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_table
    mock_table.eq.return_value = mock_table
    mock_table.order.return_value = mock_table
    mock_table.limit.return_value = mock_table
    mock_table.in_.return_value = mock_table
    mock_table.gte.return_value = mock_table
    mock_table.execute.return_value = MagicMock(data=[{"prompt_content": "## Cached Directives\n- Point 1"}])

    first = get_active_meta_directives_sync(client=mock_client)
    assert "## Cached Directives" in first
    initial_call_count = mock_client.table.call_count
    assert initial_call_count > 0

    # Second call should use cache, not hit DB
    second = get_active_meta_directives_sync(client=mock_client)
    assert second == first
    assert mock_client.table.call_count == initial_call_count

    # Clear cache and verify DB is hit again
    clear_meta_directives_cache()
    third = get_active_meta_directives_sync(client=mock_client)
    assert third == first
    assert mock_client.table.call_count > initial_call_count
