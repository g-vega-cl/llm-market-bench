"""Hermetic TDD tests for Rendezvous-Hashed multi-turn session-sticky routing in free-llm-proxy."""

from fastapi.testclient import TestClient

from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.discovery import ModelDiscovery
from apps.free_llm_proxy.router import Router
from apps.free_llm_proxy.session import (
    SESSION_HEADER,
    derive_session_id,
    resolve_routing_session_id,
)


def _make_router() -> Router:
    cb = CircuitBreaker(default_cooldown_seconds=60)
    disc = ModelDiscovery()
    r = Router(circuit_breaker=cb, discovery=disc)
    r.providers = {
        "groq": {
            "base_url": "https://api.groq.com/v1",
            "requires_auth": False,
            "tier": 1,
            "enabled_in_auto": True,
            "max_prompt_tokens": 8000,
        },
        "gemini": {
            "base_url": "https://gemini.example/v1",
            "requires_auth": False,
            "tier": 1,
            "enabled_in_auto": True,
        },
        "kilo": {
            "base_url": "https://kilo.example/v1",
            "requires_auth": False,
            "tier": 1,
            "enabled_in_auto": True,
        },
        "nous": {
            "base_url": "https://nous.example/v1",
            "requires_auth": False,
            "tier": 1,
            "enabled_in_auto": True,
        },
    }
    return r


def test_session_id_pins_primary_provider_across_turns():
    """Repeated calls with the same session_id must pick the exact same primary Tier-1 provider."""
    r = _make_router()
    sid = derive_session_id(
        [{"role": "user", "content": "refactor router.py"}],
        client_ip="127.0.0.1",
        user_agent="pi/1.0",
    )
    picks = [r.get_candidate_chain("auto-go", session_id=sid)[0][0] for _ in range(8)]
    assert len(set(picks)) == 1, (
        f"Expected sticky primary provider across turns, got {picks}"
    )


def test_rendezvous_hashing_prevents_cache_reshuffle_when_groq_drops_above_8k_tokens():
    """Sessions pinned to gemini/kilo/nous must stay on the exact same provider when groq drops out past 8k tokens."""
    r = _make_router()
    preserved = 0
    for i in range(40):
        sid = f"fllm-session-{i:04d}"
        under_8k = r.get_candidate_chain("auto-go", prompt_tokens=2000, session_id=sid)[
            0
        ][0]
        if under_8k == "groq":
            continue
        over_8k = r.get_candidate_chain("auto-go", prompt_tokens=9500, session_id=sid)[
            0
        ][0]
        assert over_8k == under_8k, (
            f"Session {sid} reshuffled from {under_8k} to {over_8k} when groq dropped!"
        )
        preserved += 1
    assert preserved > 15


def test_developer_role_single_turn_stays_stateless():
    """A single-turn developer+user call without x-opencode-session must return None for stateless round-robin."""
    msgs = [
        {"role": "developer", "content": "Extract JSON."},
        {"role": "user", "content": "Input blob."},
    ]
    assert (
        resolve_routing_session_id(msgs, client_ip="127.0.0.1", user_agent="engine")
        is None
    )


def test_session_sticky_fails_over_when_primary_cools_down():
    """If the sticky primary provider trips a 429 cooldown, routing must promote the next healthy candidate."""
    r = _make_router()
    sid = "fllm-0123456789abcdef0123456789abcdef"
    initial_primary = r.get_candidate_chain("auto-go", session_id=sid)[0][0]

    r.circuit_breaker.record_failure(initial_primary, status_code=429)
    failover_chain = [
        p_id for p_id, _ in r.get_candidate_chain("auto-go", session_id=sid)
    ]

    assert failover_chain[0] != initial_primary
    assert r.circuit_breaker.is_healthy(failover_chain[0])


def test_stateless_single_turn_calls_preserve_round_robin():
    """Calls without session_id must continue rotating across healthy Tier-1 providers."""
    r = _make_router()
    picks = [r.get_candidate_chain("auto-go")[0][0] for _ in range(4)]
    assert len(set(picks)) == 4, (
        f"Expected full round-robin rotation across 4 providers, got {picks}"
    )


def test_server_uses_sticky_session_for_multi_turn_conversations(monkeypatch):
    """POST /v1/chat/completions must pass a derived session_id on multi-turn chats or explicit session header."""
    from apps.free_llm_proxy import config, server

    monkeypatch.setattr(config, "MASTER_KEY", "test-master")
    captured_session_ids: list[str | None] = []
    real_router = _make_router()
    orig_get_chain = real_router.get_candidate_chain

    def spy_get_chain(
        requested_model: str,
        prompt_tokens: int | None = None,
        session_id: str | None = None,
    ):
        captured_session_ids.append(session_id)
        return orig_get_chain(
            requested_model, prompt_tokens=prompt_tokens, session_id=session_id
        )

    monkeypatch.setattr(real_router, "get_candidate_chain", spy_get_chain)
    monkeypatch.setattr(server, "router", real_router)

    async def fake_fetch_models(p_id, base_url, headers):
        return ["model-a"]

    async def fake_execute_completion(*, provider_cfg, payload, stream):
        return (
            200,
            {
                "id": "chatcmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 2,
                    "total_tokens": 12,
                },
            },
            {},
        )

    monkeypatch.setattr(server.discovery, "fetch_live_models", fake_fetch_models)
    monkeypatch.setattr(server, "execute_completion", fake_execute_completion)

    client = TestClient(server.app)
    auth = {"Authorization": "Bearer test-master"}

    r1 = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={
            "model": "auto-go",
            "messages": [{"role": "user", "content": "clean this newsletter"}],
        },
    )
    assert r1.status_code == 200
    assert captured_session_ids[-1] is None

    turn2_msgs = [
        {"role": "system", "content": "You are Pi."},
        {"role": "user", "content": "fix bug in router.py"},
        {"role": "assistant", "content": "Reading file..."},
        {"role": "user", "content": "apply patch"},
    ]
    turn3_msgs = [
        *turn2_msgs,
        {"role": "assistant", "content": "Patched."},
        {"role": "user", "content": "run pytest"},
    ]

    res2 = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={"model": "auto-go", "messages": turn2_msgs},
    )
    res3 = client.post(
        "/v1/chat/completions",
        headers=auth,
        json={"model": "auto-go", "messages": turn3_msgs},
    )
    assert res2.status_code == 200 and res3.status_code == 200
    assert captured_session_ids[-2] is not None
    assert captured_session_ids[-2] == captured_session_ids[-1]

    res_hdr = client.post(
        "/v1/chat/completions",
        headers={**auth, SESSION_HEADER: "ses_turn1_sticky"},
        json={
            "model": "auto-go",
            "messages": [{"role": "user", "content": "start task"}],
        },
    )
    assert res_hdr.status_code == 200
    assert captured_session_ids[-1] == "ses_turn1_sticky"
