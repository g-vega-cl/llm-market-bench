"""Output-token ceilings: the clamp only ever lowers, and never below a caller's ask."""

import pytest

from apps.free_llm_proxy import config
from apps.free_llm_proxy.request_helpers import apply_output_ceiling


def test_lowers_a_64k_request_to_a_32k_provider_ceiling():
    payload = {"max_tokens": 65536}
    apply_output_ceiling(payload, {"max_output_tokens": 32768})
    assert payload["max_tokens"] == 32768


def test_leaves_a_64k_request_alone_on_a_64k_provider():
    payload = {"max_tokens": 65536}
    apply_output_ceiling(payload, {"max_output_tokens": 65536})
    assert payload["max_tokens"] == 65536


def test_never_raises_a_smaller_request():
    payload = {"max_tokens": 4096}
    apply_output_ceiling(payload, {"max_output_tokens": 65536})
    assert payload["max_tokens"] == 4096


@pytest.mark.parametrize("key", ["max_tokens", "max_completion_tokens"])
def test_clamps_both_spellings(key):
    payload = {key: 65536}
    apply_output_ceiling(payload, {"max_output_tokens": 32768})
    assert payload[key] == 32768


def test_undeclared_provider_falls_back_to_the_env_default(monkeypatch):
    monkeypatch.setattr(config, "CLOUD_MAX_OUTPUT_TOKENS", 65536)
    payload = {"max_tokens": 200000}
    apply_output_ceiling(payload, {})
    assert payload["max_tokens"] == 65536


def test_ignores_booleans_and_junk_values():
    payload = {"max_tokens": True}
    apply_output_ceiling(payload, {"max_output_tokens": 32768})
    assert payload["max_tokens"] is True
