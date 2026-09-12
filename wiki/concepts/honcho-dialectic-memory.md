---
tags: [memory, honcho, dialectic, chat, rag, architecture, user-modeling]
category: concept
---

# Honcho & Dialectic Agent Memory

Evaluation of [Honcho](https://github.com/plastic-labs/honcho) persistent memory (as documented in the [Hermes Agent Honcho Guide](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/honcho.md)), why full adoption was deferred for `llm-market-bench`, and the specific architectural lessons retained for future implementation.

## Background: What Honcho Does

Honcho is an open-source persistent memory server developed by Plastic Labs. Instead of performing naive vector searches over raw conversational chunks, Honcho models participants ("peers") across "sessions" through background dialectic reasoning.

Its primary architectural mechanisms include:

1. **Dialectic reasoning**: An asynchronous worker evaluates dialogue exchanges after they occur to extract derived conclusions about user preferences, analytical tendencies, and implicit goals.
2. **Multi-pass reconciliation**:
   - **Pass 0**: Cold extraction or warm session inquiry.
   - **Pass 1 (Self-audit)**: Identifies gaps and checks for contradictions against prior assumptions.
   - **Pass 2 (Reconciliation)**: Resolves discrepancies and updates the peer card, preventing conflicting claims.
3. **Two-layer prompt assembly**:
   - **Base layer**: Static system constraints, tool schema, user identity card, and rolling session summaries.
   - **Dialectic layer**: Fresh LLM-synthesized context reflecting what matters right now in the active discussion.
4. **Cold vs. warm retrieval**: Automatically adjusts retrieval depth between initial queries (broad grounding on user persona) and follow-up turns (targeted causal chains and suppression of repetitive overviews).

## Why Full Adoption Was Deferred

Evaluating Honcho against the three memory tiers of `llm-market-bench` showed that immediate service integration was not warranted:

1. **Local QMD wiki (`wiki/`)**: Category mismatch. The local wiki holds static, version-controlled repository documentation. It requires zero network latency, zero API token costs, and offline availability. BM25 and local GGUF vector search via `qmd` remain the right tool.
2. **Autonomous engine pipelines (`apps/engine`)**: Batch cron jobs (pre-market analysis, consensus debate, daily predictors) require direct PostgreSQL joins against market data, newsletter snapshots, and trade records. Introducing an external memory service adds network latency, subscription dependencies, and failure points to automated market runs.
3. **Investment Chat Gateway (`apps/web`)**: Current chat usage relies on the [[concepts/private-memory-vault]], where users manually promote insights to their isolated `chat_memories` table. The volume of multi-turn user sessions does not yet justify running continuous multi-pass background LLM synthesis loops.

## Preserved Lessons for Future Revisit

If multi-turn conversational chat expands, we can implement Honcho's core patterns directly inside our existing PostgreSQL and TanStack Start stack without running a separate external service:

### 1. Multi-Pass Reconciliation for User Profiles
When enabling automatic user profiling in the chat gateway, a single extraction pass creates prompt rot. If a user states they are bullish on a stock on Monday and sell it on Thursday, naive RAG retrieves both statements.

A future learner should follow the three-pass pattern:
- **Pass 0 (Extraction)**: Parse new positions, horizons, and biases from the recent chat turn.
- **Pass 1 (Self-audit)**: Compare extracted facts against the existing user profile to locate contradictions or closed positions.
- **Pass 2 (Reconciliation)**: Synthesize an updated, conflict-free profile JSON.

To avoid user-facing latency, this process must run asynchronously in an unawaited background promise or debounced worker after the assistant message is delivered.

### 2. Two-Layer Prompt Assembly
Rather than injecting raw message arrays into a monolithic system prompt, split the context into two explicit tiers:
- **Layer 1 (Base Context)**: System persona, database schema summary, and the user's persisted profile card (investment horizon, holdings, stated risk tolerance).
- **Layer 2 (Dialectic Supplement)**: Current market regime pulled from `public.market_feeling`, plus the active inquiry focus.

### 3. Cold vs. Warm Retrieval Switching
- **Cold turns (Turn 1 or topic change)**: The system grounds itself in the user's profile card, checks today's market sentiment, and provides a direct thesis tailored to the user's style rather than an introductory encyclopedia summary.
- **Warm turns (Turns 2+, follow-ups)**: The system skips asset overviews, suppresses introductory filler, and focuses tools on granular causal records (`cause_and_effect`) or specific trade rationale.

## Schema Blueprint for User Profiles

When implemented, user profiles must maintain strict Row Level Security isolation, matching the rules in [[concepts/private-memory-vault]]:

```sql
CREATE TABLE IF NOT EXISTS public.user_chat_profiles (
    user_id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    profile_data JSONB NOT NULL DEFAULT '{
        "holdings": [],
        "watchlist": [],
        "horizon": null,
        "risk_profile": null,
        "biases": [],
        "skepticisms": []
    }'::jsonb,
    summary TEXT,
    last_reconciled_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE public.user_chat_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users access own profile"
ON public.user_chat_profiles FOR ALL
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_chat_profiles TO authenticated;
GRANT ALL ON public.user_chat_profiles TO service_role;
```

Autonomous engine trading pipelines and daily predictors must never query this table, preventing user chat notes and profile deductions from contaminating public benchmark trading decisions.

## Related

- [[entities/investment-chat-gateway]]
- [[concepts/private-memory-vault]]
- [[concepts/memory-feedback]]
- [[concepts/rag-strategy]]
- [[concepts/tool-first-agency]]
