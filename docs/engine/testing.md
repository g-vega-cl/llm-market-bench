# Testing Strategy & Execution

This document outlines the testing infrastructure for the `llm-market-bench` engine, ensuring code quality, resilience, and a warning-free developer experience.

## Quick Start

### Global (Root)
To run the full suite from the repository root:
```bash
python3 -m pytest
```

### Engine (App)
To run tests while working specifically in the engine directory:
```bash
cd apps/engine
venv/bin/python -m pytest
```

To run with verbose output:

```bash
python3 -m pytest -v
```

## Test Suites

The engine tests are located in `apps/engine/tests/` and cover the following areas:

### 1. Analysis Logic (`test_analysis_logic.py`)
- **Schema Validation**: Ensures the `DecisionObject` Pydantic model correctly validates LLM outputs.
- **Orchestration**: Verifies that `analyze_chunks` correctly spawns tasks for each model and filters out malformed input.
- **Batch Processing**: Validates that all chunks are analyzed in the same LLM call.

### 2. Resilience & Hardening (`test_resilience.py`)
- **Individual Task Failures**: Confirms that if one model fails (e.g., API timeout), the pipeline continues to process results from other models.
- **Ingestion Guardrails**: Verifies that the engine halts gracefully in `main.py` if no new newsletters are found, preventing empty data processing.

### 3. Core Utilities (`test_newsletter.py`)
- **Normalization**: Tests text cleaning, generating source IDs, and chunk hashing.
- **Extraction**: Validates email body extraction and base64 decoding.

### 4. Configuration (`test_config.py`)
- **Environment Loading**: Ensures `.env` variables are correctly loaded and mapped to the configuration constants.

## Warning-Free Policy

We maintain a strict **Zero Warning** policy for the test suite. To achieve this, we have implemented:

- **SDK Migration**: Migrated from the deprecated `google-generativeai` to the modern `google-genai` package to eliminate `FutureWarning` noise.
- **Transitive Dependency Fixes**: Pinned `pydantic<2.12.0` to resolve deprecation warnings triggered by third-party libraries (like `pyiceberg`) that have not yet updated their coding patterns.

## CI/CD Integration

Tests are automatically executed on every Push and Pull Request via GitHub Actions. A failure in any test prevents merging to the main branch.

---
*Last Updated: December 2025*
