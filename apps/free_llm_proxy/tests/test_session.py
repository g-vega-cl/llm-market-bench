"""Hermetic tests for provider session-affinity header derivation."""

from apps.free_llm_proxy.session import derive_session_id


def test_client_supplied_session_header_is_forwarded_verbatim():
    session_id = derive_session_id(
        [{"role": "user", "content": "hello"}],
        client_ip="203.0.113.7",
        user_agent="pi/1.4.0",
        provided="ses_abc123",
    )

    assert session_id == "ses_abc123"


def test_derived_session_is_stable_across_turns_of_same_conversation():
    first_turn = [{"role": "user", "content": "refactor this module"}]
    later_turn = [
        {"role": "user", "content": "refactor this module"},
        {"role": "assistant", "content": "Sure"},
        {"role": "user", "content": "now add tests"},
    ]

    first = derive_session_id(first_turn, "203.0.113.7", "pi/1.4.0")
    later = derive_session_id(later_turn, "203.0.113.7", "pi/1.4.0")

    assert first == later
    assert first.startswith("fllm-")
    assert len(first) == len("fllm-") + 32


def test_derived_session_changes_with_first_user_message():
    a = derive_session_id([{"role": "user", "content": "task A"}], "ip", "ua")
    b = derive_session_id([{"role": "user", "content": "task B"}], "ip", "ua")

    assert a != b


def test_derived_session_handles_multimodal_text_parts():
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "describe this chart"},
                {"type": "image_url", "image_url": {"url": "data:image/png;base64,xx"}},
            ],
        }
    ]

    session_id = derive_session_id(messages, "ip", "ua")

    assert session_id.startswith("fllm-")
    assert len(session_id) == len("fllm-") + 32


def test_derived_session_falls_back_to_caller_identity_without_messages():
    a = derive_session_id([], "203.0.113.7", "pi/1.4.0")
    b = derive_session_id([], "203.0.113.7", "pi/1.4.0")
    c = derive_session_id([], "198.51.100.9", "pi/1.4.0")

    assert a == b
    assert a != c


def test_control_characters_in_client_session_fall_back_to_derivation():
    session_id = derive_session_id(
        [{"role": "user", "content": "hello"}],
        client_ip="203.0.113.7",
        user_agent="pi/1.4.0",
        provided="abc\r\nX-Injected: 1",
    )

    assert session_id.startswith("fllm-")


def test_oversized_client_session_falls_back_to_derivation():
    session_id = derive_session_id(
        [{"role": "user", "content": "hello"}],
        client_ip="203.0.113.7",
        user_agent="pi/1.4.0",
        provided="a" * 200,
    )

    assert session_id.startswith("fllm-")
