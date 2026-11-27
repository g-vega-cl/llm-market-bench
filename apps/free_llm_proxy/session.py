"""Session affinity helpers for upstream gateways that require stable session IDs.

OpenCode Go rejects requests that omit ``x-opencode-session``. The proxy forwards
a client-supplied session header when present, otherwise it derives a stable ID
from the conversation's first user message plus caller identity so prompt caching
and upstream routing stay consistent across turns. Derivation is best-effort:
clients that need strict per-conversation isolation should send their own
``x-opencode-session`` value.
"""

import hashlib
import re
from typing import Any

SESSION_HEADER = "x-opencode-session"
_SESSION_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _sanitize_session_id(provided: str | None) -> str | None:
    """Accepts only short, header-safe session IDs from clients."""
    if not provided:
        return None
    candidate = provided.strip()
    return candidate if _SESSION_PATTERN.fullmatch(candidate) else None


def derive_session_id(
    messages: list[Any],
    client_ip: str,
    user_agent: str,
    provided: str | None = None,
) -> str:
    """Returns a stable session identifier for a conversation."""
    sanitized = _sanitize_session_id(provided)
    if sanitized:
        return sanitized

    seed_parts = [client_ip, user_agent]
    for message in messages:
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            seed_parts.append(content)
        elif isinstance(content, list):
            seed_parts.extend(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            )
        break

    seed = "\n".join(seed_parts)
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]
    return f"fllm-{digest}"


def resolve_routing_session_id(
    messages: list[Any] | None,
    client_ip: str,
    user_agent: str,
    provided: str | None = None,
) -> str | None:
    """Return a sticky routing session ID for multi-turn chats or explicit session headers.

    Single-turn stateless utility calls without ``x-opencode-session`` return ``None``
    so the router preserves round-robin load balancing across Tier-1 free providers.
    """
    sanitized = _sanitize_session_id(provided)
    if sanitized:
        return sanitized

    msgs = messages or []
    non_system_count = 0
    has_prior_turn = False
    for msg in msgs:
        role = msg.get("role") if isinstance(msg, dict) else getattr(msg, "role", None)
        if role and role not in {"system", "developer"}:
            non_system_count += 1
        if role in {"assistant", "tool"}:
            has_prior_turn = True

    if has_prior_turn or non_system_count > 1:
        return derive_session_id(msgs, client_ip=client_ip, user_agent=user_agent)
    return None
