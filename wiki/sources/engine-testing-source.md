---
tags: [engine, testing, quality]
category: source
---

# Source: Engine Testing Strategy

Synthesized from `raw/docs/engine/testing.md`.

## Takeaways

- **Zero Warning Policy**: Strict adherence to a warning-free test suite to ensure developer focus and catch regressions early.
- **Mocking at the Boundary**: Uses isolated unit tests for LLM handlers that mock the raw client rather than SDK internals, making tests immune to library updates.
- **Dependency Injection**: Favors DI for analysis and factory functions. All LLM client factories (e.g., `get_deepseek_client`) accept an optional `api_key` parameter to support isolated unit testing in clean CI/CD environments without patching global module states or requiring environment variables. For inline clients like `MiniMaxClient`, tests patch `core.config.MINIMAX_API_KEY` with a dummy key to bypass initialization checks while keeping client calls mocked at the boundary.
- **LLM Client Factory Mocking**: When mocking LLM clients in tests that flow through `verify_trading_decision` or similar consumers of `core.llm.clients.CLIENT_FACTORIES`, patch the **dict** (`mock_factories.get.return_value = MagicMock(...)`), not the individual factory functions (`get_deepseek_client`, etc.). The dict is populated at import time with function references, so `patch("core.llm.clients.get_deepseek_client", ...)` only replaces the module attribute — the dict still holds the original function and the real factory will run, hitting `AsyncOpenAI.__init__`'s credential check and failing in CI without `DEEPSEEK_API_KEY`. This pattern is established by every test in `tests/test_verification.py` and `tests/test_verification_retry.py`; a warning comment lives above `CLIENT_FACTORIES` in `core/llm/clients.py`.
- **Reasoning Traces**: Every LLM interaction is logged and auditable via the `/reasoning` dashboard, providing a complete "thought trail" for every trade.
- **Parallel Testing (`pytest-xdist`)**: The test suite supports high-speed process-based parallel execution (`-n auto`). Because the codebase relies heavily on clean mock boundaries and isolated dependency injection, tests do not pollute each other's environments or access shared state. This enables stable parallel execution, cutting total runtime by over 50%.

## Related

- [[entities/engine]]
- [[concepts/tool-enforcement]]
- [core/llm/clients.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/core/llm/clients.py) — `CLIENT_FACTORIES` dict and the dict-patching convention warning
- [tests/test_verification.py](file:///Users/cesarvega/Documents/p-code/llm-market-bench/apps/engine/tests/test_verification.py) — canonical example of the pattern
