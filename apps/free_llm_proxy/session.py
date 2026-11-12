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
