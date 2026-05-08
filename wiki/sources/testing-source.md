---
tags: [source, testing, pytest]
category: source
source: docs/engine/testing.md
---

# Source: Testing Strategy & Execution

Python test infrastructure for the engine at `apps/engine/tests/`.

Key details:

- **Run**: `./apps/engine/venv/bin/python3 -m pytest`
- **7 test suites**: Analysis & LLM (9 files), Consensus & Memory (5), Execution & Portfolio (5), Validation & Market Data (7), Attribution & Pipeline (2), Resilience & Core (5), Manual verification scripts (3)
- **Zero Warning policy**: strict warning-free test suite
- **Best practices**: mocking external deps, AsyncMock for async functions, dependency injection for testability
- **CI/CD**: tests run on every push/PR, failure prevents merge
- **Reasoning Trace Audit**: `llm_reasoning_logs` table captures every LLM interaction with categorized trace browsing
