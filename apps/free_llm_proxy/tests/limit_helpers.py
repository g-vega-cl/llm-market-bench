"""Shared fixtures/helpers for the free-llm-proxy limit + money-guard tests.

Kept out of `conftest.py` so the env-var bootstrapping there stays untouched, and
named without a `test_` prefix so pytest does not try to collect it.
"""

import inspect

from apps.free_llm_proxy import config
from apps.free_llm_proxy.config import load_providers_config

HEADERS = {"Authorization": f"Bearer {config.MASTER_KEY}"}


def ok_body(payload: dict | None = None) -> dict:
    return {
        "id": "chatcmpl-thinking",
        "object": "chat.completion",
        "created": 1700000000,
        "model": (payload or {}).get("model"),
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}}],
    }


def install_chain(monkeypatch, chain: list[tuple[str, dict]]) -> None:
    """Pins the candidate chain so provider order is deterministic."""
    from apps.free_llm_proxy.server import router

    monkeypatch.setattr(router, "get_candidate_chain", lambda *a, **kw: chain)


def install_catalog(monkeypatch, models: dict[str, list[str]]) -> None:
    """Stubs live catalog discovery so paid-catalog guards are satisfied."""

    async def mock_fetch(provider_id, base_url, headers=None):
        return models.get(provider_id, [])

    monkeypatch.setattr(
        "apps.free_llm_proxy.server.discovery.fetch_live_models", mock_fetch
    )


def capture(monkeypatch, behaviour=None):
    """Records dispatched payloads; behaviour(provider_cfg) may override the result."""
    dispatched: list[tuple[str, dict]] = []

    async def mock_execute(provider_cfg, payload, stream=False, client=None):
        dispatched.append((provider_cfg.get("name"), dict(payload)))
        if behaviour is not None:
            override = behaviour(provider_cfg)
            if inspect.isawaitable(override):
                override = await override
            if override is not None:
                return override
        return 200, ok_body(payload), {}

    monkeypatch.setattr("apps.free_llm_proxy.server.execute_completion", mock_execute)
    return dispatched


def provider_cfg(provider_id: str) -> dict:
    """Returns the live providers.json entry for a provider id."""
    return load_providers_config()["providers"][provider_id]


def post(client, model: str, **extra):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "think hard"}],
        **extra,
    }
    return client.post("/v1/chat/completions", headers=HEADERS, json=body)
