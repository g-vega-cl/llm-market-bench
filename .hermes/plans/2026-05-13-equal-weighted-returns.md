# Equal-Weighted Percentage Returns — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Change `_daily_returns()` so combined portfolio score is based on equal-weighted percentage returns instead of dollar-weighted equity sums.

**Architecture:** Modify only the internals of `_daily_returns()` in `metrics.py`. Instead of summing total_equity across agents per day (which gives a $10K portfolio more influence than a $5K one), compute each agent's daily percentage return independently and average them. Signature stays `async def _daily_returns(sb_client, owner_ids, week_start, week_end) -> list[float]`. No callers change.

**Tech Stack:** Python 3.13, pytest, async/await, Supabase-py

**Current behavior:** Daily equity summed across agents → returns from combined curve (dollar-weighted).
**New behavior:** Per-agent daily returns computed independently → averaged per day (equal-weighted, percentage-only).

---

## Blast Radius

| Component | Change |
|---|---|
| `autoresearch/metrics.py:_daily_returns()` | Internals rewritten |
| `autoresearch/metrics.py:compute_wall_street_metrics()` | No change |
| `autoresearch/metrics.py:compute_score()` | No change |
| `autoresearch/evaluator.py` | No change |
| `autoresearch/runner.py` | No change |
| `autoresearch/researcher.py` | No change |
| `tests/test_autoresearch.py` | New test class added |
| All other tests | Unaffected (they monkeypatch `compute_wall_street_metrics` entirely) |

---

### Task 1: Write RED test for equal-weighted averaging in `_daily_returns`

**Objective:** Prove `_daily_returns` currently sums equity (dollar-weighted), not averages percentage returns.

**Files:**
- Modify: `apps/engine/tests/test_autoresearch.py` (append new test class at end)

**Step 1: Write the failing test**

Add at the end of `test_autoresearch.py`, before the last line:

```python
# ==============================================================================
# TDD: _daily_returns must compute equal-weighted percentage returns.
# ==============================================================================

class TestDailyReturnsEqualWeighted:
    """_daily_returns must average per-agent percentage returns, not sum equity."""

    @pytest.mark.asyncio
    async def test_two_agents_equal_weighted(self, monkeypatch):
        """Two agents: Gemini +10%, DeepSeek -20% → average = -5%"""
        from autoresearch import metrics

        # Row shape from Supabase join: portfolios!inner(owner_id) nests owner_id
        rows = [
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-04", "total_equity": 5000, "portfolios": {"owner_id": "deepseek"}},
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-05", "total_equity": 4000, "portfolios": {"owner_id": "deepseek"}},
        ]

        client, recorder = _make_async_client(data=rows)
        monkeypatch.setattr(metrics, "get_async_supabase_client", lambda: asyncio.Future())
        async def fake_client(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", fake_client)

        from datetime import date
        result = await metrics._daily_returns(
            client, {"gemini", "deepseek"},
            date(2026, 5, 4), date(2026, 5, 5)
        )

        # Gemini: (11000-10000)/10000 = +0.10
        # DeepSeek: (4000-5000)/5000 = -0.20
        # Average = -0.05
        assert len(result) == 1
        assert result[0] == pytest.approx(-0.05)
```

**Step 2: Run test to verify failure**

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/test_autoresearch.py::TestDailyReturnsEqualWeighted::test_two_agents_equal_weighted -v
```

Expected: **FAIL** — current code sums equity (10000+5000=15000, 11000+4000=15000) giving 0% return, not -5%.

**Step 3: No code yet — this is RED phase only.**

**Step 4: Commit**

```bash
git add apps/engine/tests/test_autoresearch.py
git commit -m "test: add RED test for equal-weighted _daily_returns"
```

---

### Task 2: Write RED test for single-agent case

**Objective:** Single agent should return its own daily returns unchanged (no averaging distortion).

**Files:**
- Modify: `apps/engine/tests/test_autoresearch.py` (add to TestDailyReturnsEqualWeighted)

**Step 1: Write the failing test**

```python
    @pytest.mark.asyncio
    async def test_single_agent_returns_unchanged(self, monkeypatch):
        """Single agent: +10% daily → returns [0.10]"""
        from autoresearch import metrics

        rows = [
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
        ]

        client, recorder = _make_async_client(data=rows)
        monkeypatch.setattr(metrics, "get_async_supabase_client", lambda: asyncio.Future())
        async def fake_client(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", fake_client)

        from datetime import date
        result = await metrics._daily_returns(
            client, {"gemini"},
            date(2026, 5, 4), date(2026, 5, 5)
        )

        assert len(result) == 1
        assert result[0] == pytest.approx(0.10)
```

**Step 2: Run test to verify failure**

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/test_autoresearch.py::TestDailyReturnsEqualWeighted::test_single_agent_returns_unchanged -v
```

Expected: **FAIL** — current code sums (same as single-agent, so 10%) but the test documents the contract we want.

Wait — actually, for a single agent, summing vs averaging gives the same result. So this test might PASS on the current code. That's fine — it still serves as a regression test.

**Step 3: No code yet.**

**Step 4: Commit**

```bash
git add apps/engine/tests/test_autoresearch.py
git commit -m "test: add single-agent RED test for _daily_returns"
```

---

### Task 3: Write RED test for multi-day averaging

**Objective:** Two agents, two day gaps — verify averaging works across multiple days.

**Files:**
- Modify: `apps/engine/tests/test_autoresearch.py` (add to TestDailyReturnsEqualWeighted)

**Step 1: Write the failing test**

```python
    @pytest.mark.asyncio
    async def test_two_agents_two_days(self, monkeypatch):
        """Two agents, 3 days → 2 daily returns, each averaged."""
        from autoresearch import metrics

        rows = [
            # Day 1
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-04", "total_equity": 20000, "portfolios": {"owner_id": "deepseek"}},
            # Day 2: Gemini +10%, DeepSeek -10%
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-05", "total_equity": 18000, "portfolios": {"owner_id": "deepseek"}},
            # Day 3: Gemini -9.09%, DeepSeek +11.11%
            {"date": "2026-05-06", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-06", "total_equity": 20000, "portfolios": {"owner_id": "deepseek"}},
        ]

        client, recorder = _make_async_client(data=rows)
        monkeypatch.setattr(metrics, "get_async_supabase_client", lambda: asyncio.Future())
        async def fake_client(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", fake_client)

        from datetime import date
        result = await metrics._daily_returns(
            client, {"gemini", "deepseek"},
            date(2026, 5, 4), date(2026, 5, 6)
        )

        # Day 1→2: gemini=(11000-10000)/10000=0.10, deepseek=(18000-20000)/20000=-0.10 → avg=0.0
        # Day 2→3: gemini=(10000-11000)/11000≈-0.0909, deepseek=(20000-18000)/18000≈0.1111 → avg≈0.0101
        assert len(result) == 2
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(0.0101, abs=1e-4)
```

**Step 2: Run test to verify failure**

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/test_autoresearch.py::TestDailyReturnsEqualWeighted::test_two_agents_two_days -v
```

Expected: **FAIL** — current code sums equity: Day1=30000, Day2=29000 (-3.33%), Day3=30000 (+3.45%) — different from averaged returns.

**Step 3: No code yet.**

**Step 4: Commit**

```bash
git add apps/engine/tests/test_autoresearch.py
git commit -m "test: add multi-day RED test for _daily_returns"
```

---

### Task 4: Run full RED suite to confirm all three tests fail

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/test_autoresearch.py::TestDailyReturnsEqualWeighted -v
```

Expected: 2-3 FAIL, 0-1 PASS (single-agent may pass on current code since sum=avg for one agent).

---

### Task 5: Implement equal-weighted `_daily_returns`

**Objective:** Rewrite `_daily_returns()` internals for equal-weighted percentage averaging.

**Files:**
- Modify: `apps/engine/autoresearch/metrics.py` (replace `_daily_returns` body)

**Step 1: Replace `_daily_returns` body**

Replace the function body (lines 15-48) with:

```python
async def _daily_returns(sb_client, owner_ids: frozenset | set, week_start: date, week_end: date) -> list[float]:
    """Extract daily percentage returns, equal-weighted across agents.

    Each agent's daily returns are computed independently from its own
    equity curve, then averaged per day. A $10K portfolio and a $5K
    portfolio have equal weight — only percentage changes matter.

    Returns a list of averaged daily returns (one float per day gap).
    """
    from collections import defaultdict

    owner_list = list(owner_ids)
    res = (
        sb_client.table("portfolio_performance")
        .select("date, total_equity, portfolios!inner(owner_id)")
        .in_("portfolios.owner_id", owner_list)
        .gte("date", week_start.isoformat())
        .lte("date", week_end.isoformat())
        .order("date")
        .execute()
    )
    rows = (await res).data or []
    if len(rows) < 2:
        return []

    # Group equity by (owner_id, date)
    agent_equity: dict[str, dict[str, float]] = defaultdict(dict)
    for row in rows:
        owner = row["portfolios"]["owner_id"]
        d = row["date"]
        eq = float(row["total_equity"] or 0)
        agent_equity[owner][d] = eq

    # All unique dates across all agents, sorted
    all_dates = sorted({row["date"] for row in rows})

    # For each day gap, compute per-agent returns, then average
    returns = []
    for i in range(1, len(all_dates)):
        prev_date = all_dates[i - 1]
        curr_date = all_dates[i]

        agent_daily_returns = []
        for owner, equity_by_date in agent_equity.items():
            prev_eq = equity_by_date.get(prev_date)
            curr_eq = equity_by_date.get(curr_date)
            if prev_eq is not None and curr_eq is not None and prev_eq > 0:
                agent_daily_returns.append((curr_eq - prev_eq) / prev_eq)

        if agent_daily_returns:
            avg_return = sum(agent_daily_returns) / len(agent_daily_returns)
            returns.append(avg_return)

    return returns
```

**Step 2: No other files changed.**

**Step 3: Commit**

```bash
git add apps/engine/autoresearch/metrics.py
git commit -m "feat: equal-weighted percentage returns in _daily_returns"
```

---

### Task 6: Verify GREEN — run new tests

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/test_autoresearch.py::TestDailyReturnsEqualWeighted -v
```

Expected: **3 PASSED**

---

### Task 7: Run full test suite for regressions

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/ -q
```

Expected: **All tests pass** — no regressions since no other test exercises `_daily_returns` directly.

---

### Task 8: Edge case test — missing day for one agent

**Objective:** If one agent has data for a date but the other doesn't, use only the available agent's return.

**Files:**
- Modify: `apps/engine/tests/test_autoresearch.py` (add to TestDailyReturnsEqualWeighted)

**Step 1: Write the test**

```python
    @pytest.mark.asyncio
    async def test_missing_day_one_agent(self, monkeypatch):
        """DeepSeek missing on Day 2 → use Gemini's return alone."""
        from autoresearch import metrics

        rows = [
            {"date": "2026-05-04", "total_equity": 10000, "portfolios": {"owner_id": "gemini"}},
            {"date": "2026-05-04", "total_equity": 5000, "portfolios": {"owner_id": "deepseek"}},
            {"date": "2026-05-05", "total_equity": 11000, "portfolios": {"owner_id": "gemini"}},
            # deepseek missing on 2026-05-05
        ]

        client, recorder = _make_async_client(data=rows)
        monkeypatch.setattr(metrics, "get_async_supabase_client", lambda: asyncio.Future())
        async def fake_client(): return client
        monkeypatch.setattr(metrics, "get_async_supabase_client", fake_client)

        from datetime import date
        result = await metrics._daily_returns(
            client, {"gemini", "deepseek"},
            date(2026, 5, 4), date(2026, 5, 5)
        )

        # Only Gemini has data for both days: +10%
        assert len(result) == 1
        assert result[0] == pytest.approx(0.10)
```

**Step 2: Run to verify GREEN**

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/test_autoresearch.py::TestDailyReturnsEqualWeighted::test_missing_day_one_agent -v
```

Expected: **PASS** (the `if prev_eq is not None and curr_eq is not None` guard handles this).

**Step 3: Run full suite**

```bash
./apps/engine/venv/bin/python3 -m pytest apps/engine/tests/ -q
```

**Step 4: Commit**

```bash
git add apps/engine/tests/test_autoresearch.py
git commit -m "test: add missing-day edge case for _daily_returns"
```

---

## Summary

| Task | What | RED/GREEN |
|---|---|---|
| 1 | Test: two agents different returns → average | RED |
| 2 | Test: single agent → own returns | RED (may pass) |
| 3 | Test: two agents, two day gaps | RED |
| 4 | Run RED suite, confirm failures | RED verify |
| 5 | Implement equal-weighted _daily_returns | GREEN |
| 6 | Run new tests, confirm all pass | GREEN verify |
| 7 | Full test suite for regressions | REGRESSION |
| 8 | Edge case: missing day for one agent | GREEN add |

**Total files changed:** 2
- `apps/engine/autoresearch/metrics.py` — 1 function body rewritten
- `apps/engine/tests/test_autoresearch.py` — 1 new test class appended

**What stays the same:**
- `compute_wall_street_metrics` — unchanged
- `compute_score` — unchanged
- `evaluate_week` — unchanged
- `runner.py` — unchanged
- All existing tests — untouched (they monkeypatch `compute_wall_street_metrics`)
- The hard ratchet, safety check, researcher, deployment — all unchanged
