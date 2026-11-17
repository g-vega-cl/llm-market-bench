"""TDD suite: per-provider output ceilings and thinking-param passthrough.

Reproduces the "auto-go has no thinking cap / if it does it should be high" audit:
  - the output clamp must honour a provider's declared ceiling instead of a single
    global 16384 floor;
  - a caller's reasoning effort must reach providers that accept it and must never
    reach providers that reject it (a 400 there cools a healthy provider).

The paid-tier money guard lives in test_paid_timeout_guard.py.
"""

import pytest
from fastapi.testclient import TestClient

from apps.free_llm_proxy import config
from apps.free_llm_proxy.config import load_providers_config
from apps.free_llm_proxy.server import app
from apps.free_llm_proxy.tests.limit_helpers import (
    capture,
    install_catalog,
    install_chain,
    post,
    provider_cfg,
)


@pytest.fixture
def client():
    return TestClient(app)


# --------------------------------------------------------------------------- #
# Configuration defaults: no hidden 16k ceiling, no 45s thinking cutoff
# --------------------------------------------------------------------------- #


def test_cloud_output_ceiling_default_is_high():
    """The global fallback ceiling must not pin every provider at 16384."""
    assert config.CLOUD_MAX_OUTPUT_TOKENS >= 32768


def test_cloud_timeout_default_exceeds_the_old_cap():
    """Looser than the old 45s, yet below the engine clients' own patience."""
    assert 45.0 < config.CLOUD_REQUEST_TIMEOUT_SECONDS <= 180.0


def test_paid_timeout_guard_enabled_by_default():
    """A timeout on a free provider must not be allowed to buy paid tokens."""
    assert config.PAID_TIMEOUT_GUARD is True


def test_provider_catalog_declares_output_ceilings():
    """Every cloud provider declares its own max_output_tokens (Strata exempt)."""
    providers = load_providers_config()["providers"]
    missing = [
        p_id
        for p_id, p_cfg in providers.items()
        if p_id != "strata" and not isinstance(p_cfg.get("max_output_tokens"), int)
    ]
    assert missing == [], f"providers missing max_output_tokens: {missing}"


def test_provider_catalog_declares_only_known_thinking_params():
    allowed = {"reasoning_effort", "reasoning"}
    providers = load_providers_config()["providers"]
    for p_id, p_cfg in providers.items():
        declared = set(p_cfg.get("thinking_params") or [])
        assert declared <= allowed, (
            f"{p_id} declares unknown thinking param: {declared}"
        )


# --------------------------------------------------------------------------- #
# Output clamp: min(requested, provider ceiling)
# --------------------------------------------------------------------------- #


def test_clamp_uses_gemini_declared_ceiling(client, monkeypatch):
    """A 131k request against gemini lands on gemini's declared ceiling, not 16384."""
    install_chain(monkeypatch, [("gemini", provider_cfg("gemini"))])
    install_catalog(monkeypatch, {"gemini": ["gemini-3.8-flash"]})
    dispatched = capture(monkeypatch)

    resp = post(client, "gemini/gemini-3.8-flash", max_tokens=131072)

    assert resp.status_code == 200
    ceiling = provider_cfg("gemini")["max_output_tokens"]
    assert dispatched[0][1]["max_tokens"] == ceiling
    assert ceiling > 16384


def test_clamp_honours_lower_provider_ceiling(client, monkeypatch):
    """A provider with a modest ceiling still clamps down, never up."""
    install_chain(monkeypatch, [("ovhcloud", provider_cfg("ovhcloud"))])
    install_catalog(monkeypatch, {"ovhcloud": ["gpt-oss-120b"]})
    dispatched = capture(monkeypatch)

    resp = post(client, "ovhcloud/gpt-oss-120b", max_tokens=131072)

    assert resp.status_code == 200
    assert (
        dispatched[0][1]["max_tokens"] == provider_cfg("ovhcloud")["max_output_tokens"]
    )


def test_clamp_falls_back_to_global_when_undeclared(client, monkeypatch):
    """A provider without a declared ceiling falls back to the global default."""
    install_chain(
        monkeypatch,
        [
            (
                "nvidia",
                {"name": "NVIDIA NIM", "base_url": "https://nim.test/v1", "tier": 2},
            )
        ],
    )
    install_catalog(monkeypatch, {"nvidia": ["nvidia/nemotron-3-ultra-550b-a55b"]})
    dispatched = capture(monkeypatch)

    resp = post(client, "nvidia/nemotron-3-ultra-550b-a55b", max_tokens=131072)

    assert resp.status_code == 200
    assert dispatched[0][1]["max_tokens"] == config.CLOUD_MAX_OUTPUT_TOKENS


def test_clamp_applies_to_max_completion_tokens(client, monkeypatch):
    """Both OpenAI output-token spellings are clamped."""
    install_chain(monkeypatch, [("gemini", provider_cfg("gemini"))])
    install_catalog(monkeypatch, {"gemini": ["gemini-3.8-flash"]})
    dispatched = capture(monkeypatch)

    resp = post(client, "gemini/gemini-3.8-flash", max_completion_tokens=131072)

    assert resp.status_code == 200
    assert (
        dispatched[0][1]["max_completion_tokens"]
        == provider_cfg("gemini")["max_output_tokens"]
    )


def test_small_request_is_not_inflated(client, monkeypatch):
    """The clamp only ever lowers a caller's budget."""
    install_chain(monkeypatch, [("gemini", provider_cfg("gemini"))])
    install_catalog(monkeypatch, {"gemini": ["gemini-3.8-flash"]})
    dispatched = capture(monkeypatch)

    post(client, "gemini/gemini-3.8-flash", max_tokens=700)

    assert dispatched[0][1]["max_tokens"] == 700


# --------------------------------------------------------------------------- #
# Thinking passthrough: declared providers keep it, undeclared ones never see it
# --------------------------------------------------------------------------- #


def test_reasoning_effort_reaches_gemini(client, monkeypatch):
    """Gemini accepts reasoning_effort, so it must survive the rewrite."""
    install_chain(monkeypatch, [("gemini", provider_cfg("gemini"))])
    install_catalog(monkeypatch, {"gemini": ["gemini-3.8-flash"]})
    dispatched = capture(monkeypatch)

    resp = post(client, "gemini/gemini-3.8-flash", reasoning_effort="high")

    assert resp.status_code == 200
    assert dispatched[0][1]["reasoning_effort"] == "high"


def test_reasoning_effort_stripped_for_undeclared_provider(client, monkeypatch):
    """Gateways that 400 on unknown fields must never receive reasoning_effort."""
    install_chain(monkeypatch, [("ovhcloud", provider_cfg("ovhcloud"))])
    install_catalog(monkeypatch, {"ovhcloud": ["gpt-oss-120b"]})
    dispatched = capture(monkeypatch)

    resp = post(
        client,
        "ovhcloud/gpt-oss-120b",
        reasoning_effort="high",
        reasoning={"effort": "high"},
    )

    assert resp.status_code == 200
    payload = dispatched[0][1]
    assert "reasoning_effort" not in payload
    assert "reasoning" not in payload


def test_reasoning_effort_translated_for_openrouter(client, monkeypatch):
    """OpenRouter takes a normalized reasoning object; both spellings converge."""
    install_chain(monkeypatch, [("openrouter", provider_cfg("openrouter"))])
    install_catalog(monkeypatch, {"openrouter": ["openrouter/free"]})
    dispatched = capture(monkeypatch)

    resp = post(client, "openrouter/free", reasoning_effort="high")

    assert resp.status_code == 200
    payload = dispatched[0][1]
    assert "reasoning_effort" not in payload
    assert payload["reasoning"] == {"effort": "high"}


def test_reasoning_object_passthrough_for_openrouter(client, monkeypatch):
    """An explicit reasoning object is preserved verbatim for OpenRouter."""
    install_chain(monkeypatch, [("openrouter", provider_cfg("openrouter"))])
    install_catalog(monkeypatch, {"openrouter": ["openrouter/free"]})
    dispatched = capture(monkeypatch)

    post(client, "openrouter/free", reasoning={"max_tokens": 8192})

    assert dispatched[0][1]["reasoning"] == {"max_tokens": 8192}


def test_reasoning_budget_tokens_banded_for_gemini(client, monkeypatch):
    """A Strata-style budget is translated to effort instead of vanishing."""
    install_chain(monkeypatch, [("gemini", provider_cfg("gemini"))])
    install_catalog(monkeypatch, {"gemini": ["gemini-3.8-flash"]})
    dispatched = capture(monkeypatch)

    post(client, "gemini/gemini-3.8-flash", reasoning_budget_tokens=12288)

    payload = dispatched[0][1]
    assert "reasoning_budget_tokens" not in payload
    assert payload["reasoning_effort"] == "high"


def test_explicit_effort_wins_over_banded_budget(client, monkeypatch):
    """An explicit reasoning_effort is never overridden by a budget translation."""
    install_chain(monkeypatch, [("gemini", provider_cfg("gemini"))])
    install_catalog(monkeypatch, {"gemini": ["gemini-3.8-flash"]})
    dispatched = capture(monkeypatch)

    post(
        client,
        "gemini/gemini-3.8-flash",
        reasoning_effort="low",
        reasoning_budget_tokens=12288,
    )

    assert dispatched[0][1]["reasoning_effort"] == "low"
