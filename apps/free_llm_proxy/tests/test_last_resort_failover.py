"""TDD suite: the never-unanswered contract for *-go requests.

What is pinned here:

1. Money control is routing: a paid provider is only admitted to a ``*-go``
   chain, so free-only aliases can never buy tokens. The ``*-go`` aliases reach
   their paid last resort even after a free provider timed out.
2. Inside a plan-bearing provider (OpenCode Go) the plan-included models are
   spent first, then exactly one metered model — the pinned
   ``deepseek-v4.1-flash`` when the live catalog lists it.
3. A pass is bounded by one deadline per segment, re-checked before *every*
   dispatch (attempt loop and cascade), so no provider can spend the budget
   several times over and the caller's own 180s timeout never fires first.
4. Futile retries stop: a per-day/quota 429 ends the in-provider cascade, and a
   budget too small to be useful skips instead of blaming the provider.
"""

import json

import pytest
from fastapi.testclient import TestClient

from apps.free_llm_proxy import config, server
from apps.free_llm_proxy.failover import (
    MIN_ATTEMPT_SECONDS,
    attempt_budget,
    plan_models,
)
from apps.free_llm_proxy.server import app
from apps.free_llm_proxy.tests.limit_helpers import (
    install_catalog,
    install_chain,
    post,
    provider_cfg,
)

CHAIN = [("kilo", "kilo"), ("opencode-go", "opencode-go")]
PAID_ONLY = [("opencode-go", "opencode-go")]
GEMINI_ONLY = [("gemini", "gemini")]
PLAN_MODELS = ["beam-free", "longcat-2.5-free"]
CATALOG = {
    "kilo": ["kilo-auto/free"],
    "gemini": ["gemini-3.6-flash"],
    "opencode-go": [*PLAN_MODELS, "deepseek-v4.1-flash", "kimi-k3"],
}
TIMEOUT_BODY = {
    "error": {"message": "Provider kilo.test timed out", "type": "timeout_error"}
}


@pytest.fixture
def client():
    return TestClient(app)


def _install(monkeypatch, catalog=None, chain=None) -> None:
    pinned = chain if chain is not None else CHAIN
    install_chain(monkeypatch, [(name, provider_cfg(p_id)) for name, p_id in pinned])
    install_catalog(monkeypatch, catalog if catalog is not None else CATALOG)


def _dispatch(monkeypatch, decide):
    """Records (provider name, payload) and lets the test decide each result.

    ``decide(provider_cfg, payload)`` returns None for success or a
    ``(status, body, headers)`` tuple. Payload-aware, unlike the shared helper,
    because the paid resort is selected by model inside one provider.
    """
    dispatched: list[tuple[str, dict]] = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        dispatched.append((provider_cfg.get("name"), dict(payload)))
        override = decide(provider_cfg, payload)
        if override is not None:
            return override
        if stream:

            async def chunks():
                yield b'data: {"choices": [{"delta": {"content": "ok"}}]}\n\n'
                yield b'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}\n\n'
                yield b"data: [DONE]\n\n"

            return 200, chunks(), {}
        return (
            200,
            {"choices": [{"message": {"role": "assistant", "content": "ok"}}]},
            {},
        )

    monkeypatch.setattr(server, "execute_completion", mock_execute)
    return dispatched


def _free_times_out(provider_cfg_, payload):
    """Free providers blow the wall clock; a paid dispatch would succeed."""
    if provider_cfg_.get("billing") == "paid":
        return None
    return 504, TIMEOUT_BODY, {}


def _paid_models(dispatched):
    return [payload["model"] for name, payload in dispatched if name == "OpenCode Go"]


def _budget_sequence(monkeypatch, free_values):
    """Feeds the free segment a scripted budget, leaving the paid segment alone."""
    values = iter(free_values)

    def fake_segment_remaining(started, deadline):
        if deadline == config.PAID_PASS_DEADLINE_SECONDS:
            return 1000.0
        return next(values, -1.0)

    monkeypatch.setattr(server, "segment_remaining_s", fake_segment_remaining)


# --------------------------------------------------------------------------- #
# 1. Routing is the money control; *-go still reaches its paid resort
# --------------------------------------------------------------------------- #


def test_auto_go_reaches_paid_after_free_timeout(client, monkeypatch):
    """auto-go means 'free pool, then Go': a free timeout must not 502 it."""
    _install(monkeypatch)
    dispatched = _dispatch(monkeypatch, _free_times_out)

    resp = post(client, "auto-go")

    assert [name for name, _ in dispatched] == ["Kilo Code", "OpenCode Go"]
    assert resp.status_code == 200


def test_strata_auto_go_reaches_paid_after_timeout(client, monkeypatch):
    """The other *-go aliases share auto-go's paid last resort."""
    _install(monkeypatch)
    dispatched = _dispatch(monkeypatch, _free_times_out)

    resp = post(client, "strata-auto-go")

    assert [name for name, _ in dispatched][-1] == "OpenCode Go"
    assert resp.status_code == 200


def test_free_aliases_never_get_a_paid_candidate(monkeypatch):
    """The paid tier is unreachable for a free alias at the routing layer.

    This is the protection ``PAID_TIMEOUT_GUARD`` used to be documented as: it
    lives in the router's ``auto_aliases`` allowlist, not in a timeout branch.
    """
    from apps.free_llm_proxy.router import Router

    monkeypatch.setenv("OPENCODE_GO_API_KEY", "oc_sk_test")
    router = Router()

    for alias in ("free-auto", "free-fast", "auto-strata", "strata-auto"):
        paid = [
            p_id
            for p_id, p_cfg in router.get_candidate_chain(alias)
            if p_cfg.get("billing") == "paid"
        ]
        assert paid == [], f"{alias} admitted a paid provider: {paid}"

    chain = [p_id for p_id, _ in router.get_candidate_chain("auto-go")]
    assert "opencode-go" in chain


# --------------------------------------------------------------------------- #
# 2. Plan-included models first, one metered model last
# --------------------------------------------------------------------------- #


def test_opencode_go_tries_plan_models_before_last_resort(client, monkeypatch):
    """Within Go, the subscription-included models are spent before a metered one."""
    _install(monkeypatch, chain=PAID_ONLY)
    dispatched = _dispatch(monkeypatch, lambda provider_cfg_, payload: None)

    post(client, "auto-go")

    assert _paid_models(dispatched)[0] in PLAN_MODELS


def test_opencode_go_falls_back_to_deepseek_flash_last(client, monkeypatch):
    """Every plan model failing moves the paid tier to deepseek-v4.1-flash."""
    _install(monkeypatch, chain=PAID_ONLY)

    def plan_models_rate_limited(provider_cfg_, payload):
        if payload["model"] in PLAN_MODELS:
            return 429, {"error": {"message": "rate limited"}}, {"retry-after": "1"}
        return None

    dispatched = _dispatch(monkeypatch, plan_models_rate_limited)

    resp = post(client, "auto-go")

    paid = _paid_models(dispatched)
    assert paid[: len(PLAN_MODELS)] == PLAN_MODELS
    assert paid[len(PLAN_MODELS)] == "deepseek-v4.1-flash"
    assert resp.status_code == 200


def test_only_one_metered_model_is_dispatched_per_request(client, monkeypatch):
    """A failed metered attempt must not be followed by a second metered model."""
    _install(monkeypatch, chain=PAID_ONLY)
    dispatched = _dispatch(
        monkeypatch,
        lambda provider_cfg_, payload: (
            429,
            {"error": {"message": "rate limited"}},
            {"retry-after": "1"},
        ),
    )

    post(client, "auto-go")

    metered = [model for model in _paid_models(dispatched) if model not in PLAN_MODELS]
    assert metered == ["deepseek-v4.1-flash"]


def test_opencode_go_without_pinned_last_resort_uses_catalog_model(client, monkeypatch):
    """A retired or renamed pin must not become a 502 the caller cannot fix."""
    _install(
        monkeypatch,
        catalog={"kilo": ["kilo-auto/free"], "opencode-go": ["kimi-k3"]},
        chain=PAID_ONLY,
    )
    dispatched = _dispatch(
        monkeypatch,
        lambda provider_cfg_, payload: (
            429,
            {"error": {"message": "rate limited"}},
            {"retry-after": "1"},
        ),
    )

    resp = post(client, "auto-go")

    # Grounded in the provider's own catalog, never the absent pinned id.
    assert _paid_models(dispatched) == ["kimi-k3"]
    assert resp.status_code == 502


def test_explicit_opencode_go_target_keeps_requested_model(client, monkeypatch):
    """A deliberate opencode-go/<model> request is not reordered."""
    _install(monkeypatch, chain=PAID_ONLY)
    dispatched = _dispatch(monkeypatch, lambda provider_cfg_, payload: None)

    resp = post(client, "opencode-go/kimi-k3")

    assert _paid_models(dispatched) == ["kimi-k3"]
    assert resp.status_code == 200


def test_plan_pattern_mismatch_is_logged(caplog):
    """A renamed plan model must not silently turn the provider into 'spend first'."""
    provider = {"name": "OpenCode Go", "free_model_patterns": ["*free*"]}
    with caplog.at_level("WARNING", logger="free_llm_proxy.failover"):
        assert plan_models(provider, ["deepseek-v4.1-flash"]) == []
    assert "metered" in caplog.text


# --------------------------------------------------------------------------- #
# 3. One deadline per segment, enforced at every dispatch
# --------------------------------------------------------------------------- #


def test_attempt_budget_skips_short_remainders():
    """A remainder too small to finish is a skip, never a zero-second dispatch."""
    assert attempt_budget({}, MIN_ATTEMPT_SECONDS - 0.5).skip is True
    assert attempt_budget({}, -3.0).skip is True
    # A useful remainder clamps the attempt to it.
    assert attempt_budget({}, 3.0).cap_s == 3.0
    assert attempt_budget({}, 1000.0).cap_s == config.FREE_ATTEMPT_TIMEOUT_SECONDS
    assert attempt_budget({"billing": "paid"}, 1000.0).cap_s == min(
        config.PAID_ATTEMPT_TIMEOUT_SECONDS, config.CLOUD_REQUEST_TIMEOUT_SECONDS
    )


def test_free_candidates_skipped_after_free_deadline(client, monkeypatch):
    """Past the free deadline the free segment stops; the paid resort still runs."""
    _install(monkeypatch)
    _budget_sequence(monkeypatch, [-1.0, -1.0])
    dispatched = _dispatch(monkeypatch, _free_times_out)

    resp = post(client, "auto-go")

    assert [name for name, _ in dispatched] == ["OpenCode Go"]
    assert resp.status_code == 200


def test_free_deadline_is_reported_when_everything_fails(client, monkeypatch):
    """The terminal 502 names the skipped free candidates instead of hiding them."""
    _install(monkeypatch)
    _budget_sequence(monkeypatch, [-1.0, -1.0])
    _dispatch(
        monkeypatch,
        lambda provider_cfg_, payload: (
            429,
            {"error": {"message": "rate limited"}},
            {"retry-after": "1"},
        ),
    )

    resp = post(client, "auto-go")

    assert resp.status_code == 502
    chain = json.loads(resp.text)["error"]["failover_chain"]
    assert any("free pass deadline" in entry for entry in chain)


def test_cascade_stops_when_the_segment_budget_runs_out(client, monkeypatch):
    """The cascade re-checks the clock: one candidate cannot spend it N times."""
    _install(monkeypatch, catalog={"gemini": ["gemini-3.6-flash"]}, chain=GEMINI_ONLY)
    # guard, first attempt, one fallback, then the budget is gone.
    _budget_sequence(monkeypatch, [5.0, 5.0, 5.0, 0.5])
    dispatched = _dispatch(
        monkeypatch,
        lambda provider_cfg_, payload: (
            503,
            {"error": {"message": "high demand"}},
            {},
        ),
    )

    post(client, "auto-go")

    assert len(dispatched) == 2


def test_budget_expiring_mid_candidate_logs_one_skip_not_http_zero(client, monkeypatch):
    """A candidate skipped by the budget is not a provider failure (no `HTTP 0`)."""
    _install(
        monkeypatch, catalog={"kilo": ["kilo-auto/free"]}, chain=[("kilo", "kilo")]
    )
    _budget_sequence(monkeypatch, [5.0, -1.0])
    _dispatch(monkeypatch, lambda provider_cfg_, payload: None)

    resp = post(client, "free-auto")

    chain = json.loads(resp.text)["error"]["failover_chain"]
    assert chain == ["kilo (skipped: free pass deadline exhausted)"]


def test_streaming_is_not_cut_by_the_free_deadline(client, monkeypatch):
    """An interactive stream keeps its own patience; the budget is a utility guard."""
    _install(monkeypatch)
    _budget_sequence(monkeypatch, [-1.0, -1.0])
    dispatched = _dispatch(monkeypatch, lambda provider_cfg_, payload: None)

    resp = post(client, "auto-go", stream=True)

    assert [name for name, _ in dispatched][0] == "Kilo Code"
    assert resp.status_code == 200


# --------------------------------------------------------------------------- #
# 4. Futile retries stop
# --------------------------------------------------------------------------- #


def test_daily_quota_429_skips_in_provider_cascade(client, monkeypatch):
    """A per-day quota 429 cannot succeed on a retry, so it must not be retried."""
    _install(monkeypatch, catalog={"gemini": ["gemini-3.6-flash"]}, chain=GEMINI_ONLY)
    dispatched = _dispatch(
        monkeypatch,
        lambda provider_cfg_, payload: (
            429,
            {
                "error": {
                    "message": (
                        "Generate content requests per day limit exceeded on Free Tier"
                    )
                }
            },
            {},
        ),
    )

    resp = post(client, "auto-go")

    assert len(dispatched) == 1
    assert resp.status_code == 502


def test_429_that_turns_into_a_quota_wall_stops_the_cascade(client, monkeypatch):
    """Futility is judged per response, not once at the start of the cascade."""
    _install(monkeypatch, catalog={"gemini": ["gemini-3.6-flash"]}, chain=GEMINI_ONLY)
    calls = {"n": 0}

    def transient_then_quota(provider_cfg_, payload):
        calls["n"] += 1
        if calls["n"] == 1:
            return 429, {"error": {"message": "rate limited"}}, {"retry-after": "1"}
        return (
            429,
            {"error": {"message": "tokens per day (TPD) limit reached"}},
            {"retry-after": "1"},
        )

    dispatched = _dispatch(monkeypatch, transient_then_quota)

    post(client, "auto-go")

    assert len(dispatched) == 2


def test_transient_429_still_cascades_inside_provider(client, monkeypatch):
    """A plain rate limit is still worth an adjacent model, unlike a quota wall."""
    _install(monkeypatch, catalog={"gemini": ["gemini-3.6-flash"]}, chain=GEMINI_ONLY)
    dispatched = _dispatch(
        monkeypatch,
        lambda provider_cfg_, payload: (
            429,
            {"error": {"message": "rate limited"}},
            {"retry-after": "1"},
        ),
    )

    post(client, "auto-go")

    assert len(dispatched) > 1
