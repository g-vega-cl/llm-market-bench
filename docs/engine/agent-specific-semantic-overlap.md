# Agent-Specific Semantic Overlap

Ensures the semantic redundancy check applies only within the same agent's portfolio, preserving independent decision-making across the multi-agent architecture.

## Problem

Previously, semantic overlap compared trades across ALL agents. If Claude traded NKE on earnings, Gemini was blocked from doing the same — even with a separate portfolio and independent reasoning context. This violated the multi-agent principle.

## Solution

The semantic overlap check filters by `model_name` so each agent's trades are only compared against its own recent trades. Window length and similarity threshold: `apps/engine/execution/validation.py`.

**Example:**
- Claude trades NKE → Claude is blocked from repeating NKE
- Gemini sees the same opportunity → Gemini can still trade NKE independently

## Implementation

- `find_similar_decision()` in `apps/engine/memory/store.py` accepts optional `model_name` parameter
- `find_similar_vector()` filters Supabase query by `model_name` when provided
- `validate_semantic_overlap()` in `apps/engine/execution/validation.py` passes agent identifier
- Pipeline in `main.py` calls `validate_semantic_overlap(d.ticker, d.reasoning, model_name=d.model_name)`

No database migrations required — the `model_name` column already exists in `decisions`.

## Key Files

- `apps/engine/memory/store.py` — `find_similar_decision()`, `find_similar_vector()`
- `apps/engine/execution/validation.py` — `validate_semantic_overlap()`
- `apps/engine/main.py` — Pipeline integration
