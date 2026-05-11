# Auto-Research Hardening Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Harden the auto-research module: fix Python version drift, add atomic rollback, add tests for `run_research`, make DB calls async, clean up naming/docs, improve failure logging, and add stagnation floor check.

**Architecture:** Each fix is isolated to 1-2 files. TDD throughout: write a failing test, verify RED, implement, verify GREEN. All changes stay within `apps/engine/autoresearch/`, `apps/engine/tests/`, `.github/workflows/`, and `wiki/`.

**Tech Stack:** Python 3.12, pytest + pytest-asyncio, supabase-py (sync + async), Instructor

---

## Task 1: Standardize Python Version to 3.12

**Objective:** Pin CI and production to the same Python version.

**Files:**
- Modify: `.github/workflows/autoresearch.yml:20` (change `3.12` → confirm 3.12)
- Modify: `.github/workflows/ci.yml:26` (change `3.11` → `3.12`)

**Step 1: Verify current state**

CI uses 3.11, autoresearch workflow uses 3.12. Local venv is 3.13.

**Step 2: Update CI to match production**

```yaml
# .github/workflows/ci.yml line 26
- python-version: "3.12"
```

**Step 3: Verify**

No tests to write — this is config. Run CI to confirm it passes on 3.12.

---

## Task 2: Fix `save_variant` Atomicity — Don't Demote Before Insert Succeeds

**Objective:** If the `INSERT` in `save_variant` fails, the previous active prompt must remain active. Currently it's demoted to "kept" BEFORE the insert, leaving a window with zero active prompts.

**Files:**
- Modify: `apps/engine/autoresearch/prompt_store.py:59-95`
- Modify: `apps/engine/tests/test_autoresearch.py` (add test class)

**Step 1: Write RED test**

```python
class TestSaveVariantAtomicity:
    """save_variant must not demote the active prompt until insert succeeds."""

    @pytest.mark.asyncio
    async def test_active_remains_after_insert_failure(self, monkeypatch):
        from autoresearch import prompt_store

        # Track what queries ran
        queries = []
        active_state = {"status": "active", "prompt_content": "OLD_PROMPT"}

        async def fake_client():
            client = MagicMock()

            class AtomicityRecorder:
                def __init__(self):
                    self._single_data = active_state

                def __getattr__(self, name):
                    if name.startswith("_"):
                        raise AttributeError(name)
                    def method(*args, **kwargs):
                        queries.append((name, args))
                        if name == "execute":
                            async def exec_coro():
                                if queries[-2][0] == "insert" if len(queries) >= 2 else False:
                                    # Check: was the active demoted BEFORE insert?
                                    pass
                                r = MagicMock()
                                r.data = self._single_data
                                return r
                            return exec_coro()
                        elif name == "update":
                            # Simulate: the update to demote old active succeeds
                            pass
                        elif name == "insert":
                            # Simulate: the insert FAILS
                            raise Exception("Simulated insert failure")
                        return self
                    return method

            client.table.return_value = AtomicityRecorder()
            return client

        monkeypatch.setattr(prompt_store, "get_async_supabase_client", fake_client)
        prompt_store.clear_active_prompt_cache()

        # save_variant should raise or handle the error
        with pytest.raises(Exception, match="Simulated insert failure"):
            await prompt_store.save_variant(
                prompt_content="NEW_PROMPT",
                prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
                week_start="2026-05-04",
                week_end="2026-05-10",
                metrics={"composite": 0.5},
                change_description="test",
                experiment_type="incremental",
            )

        # After failure: the UPDATE to demote old active must NOT have run
        # The active prompt must still be active
        update_calls = [q for q in queries if q[0] == "update"]
        assert len(update_calls) == 0, (
            "UPDATE must not run before INSERT succeeds"
        )
```

Actually, the correct approach is simpler: reorder the code so the insert happens FIRST, then demote the old active. Write a test that verifies the order of operations.

**Step 1 (revised): Write RED test — verify insert runs BEFORE demotion**

```python
class TestSaveVariantAtomicity:
    @pytest.mark.asyncio
    async def test_insert_before_demotion(self, monkeypatch):
        """Insert must happen BEFORE demoting the old active prompt."""
        from autoresearch import prompt_store

        op_order = []

        async def fake_client():
            client = MagicMock()

            class OrderTracker(_QueryRecorder):
                def __getattr__(self, name):
                    if name.startswith("_"):
                        raise AttributeError(name)
                    def method(*args, **kwargs):
                        if name in ("update", "insert", "select", "eq", "execute"):
                            op_order.append(name)
                        if name == "execute":
                            async def exec_coro():
                                r = MagicMock()
                                r.data = self._single_data if self._single_data is not None else []
                                return r
                            return exec_coro()
                        return self
                    return method

            client.table.return_value = OrderTracker(single_data={"variant_tag": "v-old"})
            return client

        monkeypatch.setattr(prompt_store, "get_async_supabase_client", fake_client)
        prompt_store.clear_active_prompt_cache()

        await prompt_store.save_variant(
            prompt_content="NEW_PROMPT",
            prompt_name="CORE_ANALYSIS_SYSTEM_PROMPT",
            week_start="2026-05-04",
            week_end="2026-05-10",
            metrics={"composite": 0.5},
            change_description="test",
            experiment_type="incremental",
        )

        # Find the positions of first insert and first update in op_order
        insert_idx = next((i for i, op in enumerate(op_order) if op == "insert"), None)
        update_idx = next((i for i, op in enumerate(op_order) if op == "update"), None)

        assert insert_idx is not None, "Expected an 'insert' operation"
        assert update_idx is not None, "Expected an 'update' operation"
        assert insert_idx < update_idx, (
            f"INSERT must happen BEFORE UPDATE (demotion). "
            f"Got insert at {insert_idx}, update at {update_idx}"
        )
```

**Step 2: Run test — verify RED**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py::TestSaveVariantAtomicity -v
```

Expected: FAIL — insert_idx > update_idx (current code demotes first)

**Step 3: Fix `save_variant` — reorder operations**

In `prompt_store.py`, move the demotion UPDATE to AFTER the insert:

```python
async def save_variant(...) -> str:
    sb_client = await get_async_supabase_client()
    
    now = datetime.now(timezone.utc)
    tag = f"v{now.strftime('%Y%m%d-%H%M%S')}"

    insert_data: dict[str, Any] = {
        "variant_tag": tag,
        "prompt_name": prompt_name,
        "prompt_content": prompt_content,
        "week_start": week_start,
        "week_end": week_end,
        "metrics": metrics,
        "status": "active",
        "experiment_type": experiment_type,
        "parent_tag": parent_tag,
        "change_description": change_description,
        "research_output": research_output,
    }

    # INSERT FIRST — if this fails, nothing is lost
    await sb_client.table("prompt_experiments").insert(insert_data).execute()

    # NOW demote the previous active — the new one is safely in place
    await sb_client.table("prompt_experiments").update({"status": "kept"}).eq(
        "status", "active"
    ).eq("prompt_name", prompt_name).neq("variant_tag", tag).execute()

    clear_active_prompt_cache()
    logger.info("Saved prompt variant %s (type=%s)", tag, experiment_type)
    return tag
```

Note: Add `.neq("variant_tag", tag)` to the demotion UPDATE so we don't demote the one we just inserted.

**Step 4: Run test — verify GREEN**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py::TestSaveVariantAtomicity -v
```

Expected: PASS

**Step 5: Run full suite — verify no regressions**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/ -v
```

Expected: All 43 tests pass (42 existing + 1 new)

**Step 6: Commit**

```bash
git add apps/engine/autoresearch/prompt_store.py apps/engine/tests/test_autoresearch.py
git commit -m "fix: make save_variant atomic — insert before demoting old active"
```

---

## Task 3: Add Tests for `run_research` Retry Loop

**Objective:** The `run_research` function in `researcher.py` has a 3-attempt retry loop with error classification (validation errors → retry, non-retryable → raise). Zero tests exist for this critical code path.

**Files:**
- Modify: `apps/engine/tests/test_autoresearch.py` (add `TestResearcherRetry` class)

**Step 1: Write RED test — retries on validation error**

```python
class TestResearcherRetry:
    """run_research must retry on validation errors and give up on non-retryable."""

    @pytest.mark.asyncio
    async def test_retries_on_validation_error(self, monkeypatch):
        from autoresearch import researcher

        call_count = {"n": 0}

        class FakeWrapper:
            pass  # Successful response on 3rd try

        async def fake_create(**kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise Exception("validation error: input should be a valid")
            wrapper = FakeWrapper()
            return wrapper

        # Mock the client
        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report")
        assert result is not None
        assert call_count["n"] == 3, f"Expected 3 attempts, got {call_count['n']}"

    @pytest.mark.asyncio
    async def test_raises_on_non_retryable_error(self, monkeypatch):
        from autoresearch import researcher

        async def fake_create(**kwargs):
            raise Exception("rate limit exceeded — not a validation error")

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report")
        # Non-retryable error → returns None after logging
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_after_all_retries_exhausted(self, monkeypatch):
        from autoresearch import researcher

        call_count = {"n": 0}

        async def fake_create(**kwargs):
            call_count["n"] += 1
            # Always validation error — all 3 retries fail
            raise Exception("validation error: bad schema")

        fake_client = MagicMock()
        fake_client.chat.completions.create = fake_create

        monkeypatch.setattr(researcher, "get_deepseek_client", lambda: fake_client)

        result = await researcher.run_research("# Test Report")
        assert result is None
        assert call_count["n"] == 3, f"Expected 3 attempts, got {call_count['n']}"
```

**Step 2: Run test — verify RED**

Wait — actually, the existing code already handles these cases. The tests might pass immediately (GREEN) if we're testing existing behavior. But we need to verify:

1. The test actually tests the retry loop (not mocked away)
2. It fails for the right reason if we break the code

Let me verify: in `run_research`, the retry loop catches exceptions, checks if "validation error" is in the error string, and retries. For non-validation errors, it re-raises. The outer `try/except` catches that re-raise and returns `None`.

These tests WILL be GREEN on first run — they test existing behavior. But that's OK for hardening. The value is in preventing regressions.

**Step 2 (revised): Run test — verify it passes**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py::TestResearcherRetry -v
```

Expected: PASS (these test existing behavior)

**Step 3: Run full suite**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/ -v
```

Expected: All 45 tests pass (42 existing + 3 new)

**Step 4: Commit**

```bash
git add apps/engine/tests/test_autoresearch.py
git commit -m "test: add retry-loop tests for run_research"
```

---

## Task 4: Make DB Calls Async in `metrics.py` and `decision_quality.py`

**Objective:** `compute_wall_street_metrics` and `compute_decision_quality` use sync `get_supabase_client()` and block the event loop when called from `async def evaluate_week()`. Convert to `get_async_supabase_client()`.

**Files:**
- Modify: `apps/engine/autoresearch/metrics.py`
- Modify: `apps/engine/autoresearch/decision_quality.py`
- Modify: `apps/engine/autoresearch/evaluator.py` (add await to calls)
- Modify: `apps/engine/tests/test_autoresearch.py` (update mocks to be async)

**Step 1: Convert `metrics.py` — make `compute_wall_street_metrics` async**

Current:
```python
def compute_wall_street_metrics(owner_ids, week_start, week_end) -> dict:
    sb_client = get_supabase_client()  # sync
    ...
```

New:
```python
async def compute_wall_street_metrics(owner_ids, week_start, week_end) -> dict:
    sb_client = await get_async_supabase_client()  # async
    ...
```

Also convert internal helpers `_daily_returns`, `_spy_returns`, `_realized_pnl` to accept the async client (they don't need to be async themselves — they just receive the client object and call sync methods on it).

Wait — the supabase-py async client still uses sync method chaining like `.select().eq().execute()`. The only async part is getting the client. So internal helpers stay sync.

**Step 2: Convert `decision_quality.py` — make `compute_decision_quality` async**

Same pattern: change `get_supabase_client()` → `await get_async_supabase_client()`.

**Step 3: Update `evaluator.py` — add `await` to calls**

```python
# Before:
exp_metrics = compute_wall_street_metrics(AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end)
ctrl_metrics = compute_wall_street_metrics(CONTROL_OWNER_IDS, week_start, week_end)
dq = compute_decision_quality(AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end)

# After:
exp_metrics = await compute_wall_street_metrics(AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end)
ctrl_metrics = await compute_wall_street_metrics(CONTROL_OWNER_IDS, week_start, week_end)
dq = await compute_decision_quality(AUTORESEARCH_EXPERIMENT_OWNER_IDS, week_start, week_end)
```

**Step 4: Update tests — mock async client**

The tests mock `get_supabase_client` with `monkeypatch.setattr(module, "get_supabase_client", lambda: client)`. Need to change to mock `get_async_supabase_client` with an async function:

```python
async def fake_get_async_client():
    return client

monkeypatch.setattr(module, "get_async_supabase_client", fake_get_async_client)
```

**Step 5: Write RED test — verify async client is used**

```python
class TestAsyncDbCalls:
    def test_metrics_uses_async_client(self, monkeypatch):
        """compute_wall_street_metrics must use get_async_supabase_client."""
        from autoresearch import metrics
        called = []

        async def fake_async_client():
            called.append("async")
            client, _ = _make_client(data=[])
            return client

        monkeypatch.setattr(metrics, "get_async_supabase_client", fake_async_client)
        monkeypatch.setattr(metrics, "get_supabase_client", lambda: (_ for _ in ()).throw(AssertionError("sync client called")))

        import asyncio
        asyncio.run(metrics.compute_wall_street_metrics(
            frozenset({"m1"}), date(2026, 5, 1), date(2026, 5, 7)
        ))
        assert "async" in called, "Must use get_async_supabase_client"
```

Actually this is getting complex. Simpler approach:

**Step 5 (simplified): Verify existing tests still pass after conversion**

The existing tests mock `get_supabase_client`. After conversion, they need to mock `get_async_supabase_client` instead. Each affected test gets updated. Then run the suite:

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py -v
```

Expected: All tests pass after updating mocks.

**Step 6: Commit**

```bash
git add apps/engine/autoresearch/metrics.py apps/engine/autoresearch/decision_quality.py apps/engine/autoresearch/evaluator.py apps/engine/tests/test_autoresearch.py
git commit -m "refactor: convert autoresearch DB calls to async client"
```

---

## Task 5: Rename `_count_tokens` to `_count_words` + Fix Wiki

**Objective:** The function counts words, not tokens. The name and wiki doc are misleading.

**Files:**
- Modify: `apps/engine/autoresearch/validator.py:40-44` (rename function, update docstring)
- Modify: `apps/engine/autoresearch/validator.py:60` (update caller)
- Modify: `wiki/entities/autoresearch.md:91-92` (remove tiktoken reference)

**Step 1: Rename in validator.py**

```python
# Before:
def _count_tokens(text: str) -> int:
    """Estimate token count from word count (English: ~1.3 tokens per word).
    No external library needed — conservative enough for prompt sizing."""
    return len(text.split())

# After:
def _count_words(text: str) -> int:
    """Count words via split(). Conservative cap: 1000 words.
    English text averages ~1.3 tokens/word, so 1000 words ≈ 1300 tokens."""
    return len(text.split())
```

Update caller on line 60:
```python
# Before: token_count = _count_tokens(prompt)
# After:  word_count = _count_words(prompt)
```

**Step 2: Fix wiki**

In `wiki/entities/autoresearch.md` line 91-92:
```
# Before:
- **Prompt validation**: two-tier. Hard invariants (forbidden phrases like
  "bypass guardrails", empty/oversized prompts, >1500 tokens via tiktoken
  `o200k_base` encoding) block activation.

# After:
- **Prompt validation**: two-tier. Hard invariants (forbidden phrases like
  "bypass guardrails", empty/oversized prompts, >1000 words) block activation.
```

**Step 3: Run tests**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py -v
```

Expected: All tests pass.

**Step 4: Commit**

```bash
git add apps/engine/autoresearch/validator.py wiki/entities/autoresearch.md
git commit -m "docs: rename _count_tokens → _count_words, fix wiki tiktoken reference"
```

---

## Task 6: Add Obvious Failure Logging to `runner.py`

**Objective:** When the auto-research cycle fails, make it painfully obvious in logs so the user can catch it.

**Files:**
- Modify: `apps/engine/autoresearch/runner.py`

**Step 1: Add a summary line at the end of `run()`**

At the end of `run()`, add:

```python
# At the very end, after the success path
logger.info("=== Auto-Research Cycle Complete ===")
logger.info("Next week's prompt: %s (%s)", tag, result.experiment_type)

# NEW: Add a summary that's easy to grep
logger.info("AUTORESEARCH_RESULT: SUCCESS | variant=%s | type=%s | composite=%.4f",
            tag, result.experiment_type, composite["composite"])
```

At each failure point, add a matching failure log:

```python
# After safety crash
logger.warning("AUTORESEARCH_RESULT: SKIPPED_CRASH | reason=%s", crash_reason)

# After evaluation failure
logger.error("AUTORESEARCH_RESULT: FAILED_EVALUATION | error=%s", e)

# After research returns None
logger.error("AUTORESEARCH_RESULT: FAILED_RESEARCH | reason=empty_response")

# After validation failure
logger.error("AUTORESEARCH_RESULT: FAILED_VALIDATION | reason=%s", reason)

# After save failure
logger.error("AUTORESEARCH_RESULT: FAILED_SAVE | error=%s", e)
```

**Step 2: No new tests needed** — this is logging-only, no behavior change.

**Step 3: Run tests to confirm no breakage**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py -v
```

**Step 4: Commit**

```bash
git add apps/engine/autoresearch/runner.py
git commit -m "feat: add AUTORESEARCH_RESULT summary log lines for grep-ability"
```

---

## Task 7: Add Stagnation Floor-Level Check

**Objective:** When composite scores are all near zero (e.g., [0.01, 0.02, 0.03]), the current stagnation check computes `pct_range=1.0` and says "no stagnation." This is wrong — the agent is at the floor and needs a radical variant.

**Files:**
- Modify: `apps/engine/autoresearch/evaluator.py:78-103`
- Modify: `apps/engine/tests/test_autoresearch.py` (add `TestStagnationEdgeCases`)

**Step 1: Write RED tests**

```python
class TestStagnationEdgeCases:
    def test_floor_scores_trigger_stagnation(self):
        """Scores near zero should trigger stagnation regardless of % range."""
        from autoresearch.evaluator import _check_stagnation
        variants = [
            {"metrics": {"composite": 0.01}},
            {"metrics": {"composite": 0.02}},
            {"metrics": {"composite": 0.03}},
        ]
        is_stagnant, msg = _check_stagnation(variants)
        assert is_stagnant, (
            f"Floor scores [0.01, 0.02, 0.03] must trigger stagnation; "
            f"pct_range may be large but absolute scores are terrible"
        )

    def test_normal_scores_with_variance_not_stagnant(self):
        """Scores with real variance above the floor should not trigger."""
        from autoresearch.evaluator import _check_stagnation
        variants = [
            {"metrics": {"composite": 0.50}},
            {"metrics": {"composite": 0.60}},
            {"metrics": {"composite": 0.55}},
        ]
        is_stagnant, msg = _check_stagnation(variants)
        assert not is_stagnant, (
            f"Scores [0.50, 0.60, 0.55] should not trigger stagnation"
        )

    def test_string_metrics_parsed_correctly(self):
        """Metrics stored as JSON strings must be parsed."""
        from autoresearch.evaluator import _check_stagnation
        import json
        variants = [
            {"metrics": json.dumps({"composite": 0.01})},
            {"metrics": json.dumps({"composite": 0.01})},
        ]
        is_stagnant, msg = _check_stagnation(variants)
        assert is_stagnant, "String-JSON metrics at floor must trigger stagnation"
```

**Step 2: Run tests — verify RED**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py::TestStagnationEdgeCases -v
```

Expected: `test_floor_scores_trigger_stagnation` FAILS — it currently returns `(False, "")`

**Step 3: Fix `_check_stagnation`**

Add a floor threshold alongside the 5% range check:

```python
def _check_stagnation(previous_variants: list[dict]) -> tuple[bool, str]:
    """Check if composite score has stagnated for 2+ weeks."""
    recent = [v for v in previous_variants if v.get("metrics") and isinstance(v["metrics"], dict)]
    if len(recent) < 2:
        return False, ""

    metrics_list = []
    for v in recent[:3]:
        m = v["metrics"]
        if isinstance(m, str):
            try:
                m = json.loads(m)
            except (json.JSONDecodeError, TypeError):
                continue
        comp = m.get("composite")
        if comp is not None:
            metrics_list.append(float(comp))

    if len(metrics_list) >= 2:
        avg = sum(metrics_list) / len(metrics_list)
        
        # Floor check: if average composite is below 0.05, we're stuck at the floor
        if avg < 0.05:
            return True, (
                f"STAGNATION: average composite score ({avg:.3f}) is at floor (< 0.05). "
                "A RADICAL variant is strongly recommended."
            )
        
        if avg > 0:
            pct_range = (max(metrics_list) - min(metrics_list)) / avg
            if pct_range < 0.05:
                return True, f"STAGNATION: composite score has been within {pct_range:.1%} for {len(metrics_list)} weeks. A RADICAL variant is strongly recommended."

    return False, ""
```

**Step 4: Run tests — verify GREEN**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py::TestStagnationEdgeCases -v
```

Expected: All 3 tests PASS

**Step 5: Run full suite**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/ -v
```

**Step 6: Commit**

```bash
git add apps/engine/autoresearch/evaluator.py apps/engine/tests/test_autoresearch.py
git commit -m "fix: add floor-level stagnation check for near-zero composite scores"
```

---

## Task 8: Fix `_get_market_regime_summary` — Use Async Client

**Objective:** `_get_market_regime_summary` in `evaluator.py` uses sync `get_supabase_client()`. Convert to async.

**Files:**
- Modify: `apps/engine/autoresearch/evaluator.py:25-75`
- Modify: `apps/engine/tests/test_autoresearch.py` (update `test_market_regime_queries_use_fetched_at_and_price`)

**Step 1: Make `_get_market_regime_summary` accept an optional client**

```python
async def _get_market_regime_summary(week_start: date, week_end: date, sb_client=None) -> str:
    if sb_client is None:
        sb_client = await get_async_supabase_client()
    ...
```

And call it with `await` in `evaluate_week`:

```python
regime = await _get_market_regime_summary(week_start, week_end)
```

**Step 2: Update test mock**

Change the test to mock `get_async_supabase_client` instead of `get_supabase_client`.

**Step 3: Run tests**

```bash
cd apps/engine && ./venv/bin/python3 -m pytest tests/test_autoresearch.py::TestEvaluator -v
```

**Step 4: Commit**

---

## Execution Order

1. Task 1 — Python version (config-only, no tests)
2. Task 2 — save_variant atomicity (TDD)
3. Task 3 — run_research tests (confirm existing behavior)
4. Task 4 — async DB calls (refactor with test updates)
5. Task 8 — async market regime (refactor)
6. Task 5 — rename _count_words + wiki fix (docs)
7. Task 6 — logging (no new tests)
8. Task 7 — stagnation floor check (TDD)

---

## Verification Checklist (Post-Implementation)

- [ ] `pytest tests/ -v` — all tests pass
- [ ] CI workflow uses Python 3.12
- [ ] `AUTORESEARCH_RESULT` lines appear in runner log output
- [ ] Wiki tiktoken reference removed
- [ ] `save_variant` inserts before demoting (confirmed by test)
- [ ] All DB calls in autoresearch/ use async client
- [ ] Stagnation triggers at floor (< 0.05 avg composite)
