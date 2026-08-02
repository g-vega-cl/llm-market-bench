---
tags: [uncrowded-trade, thematic-rotation, adjacent-trade, market-structure, ai-infrastructure]
category: concept
---

# Thematic Rotation & The Adjacent Trade Pattern

When a dominant market narrative peaks, capital does not exit the theme — it
rotates *within* it to the next layer of the value chain. Identifying *where*
in this rotation sequence the market currently sits is an exploitable structural
signal.

---

## The Adjacent Trade Pattern

When the primary narrative of a hype cycle stalls (e.g., AI application stocks
plateau), capital historically rotates to **ecosystem suppliers** rather than
exiting the theme entirely. This is a rational, repeatable behavioural pattern:

1. Investors remain bullish on the long-run thesis.
2. They exit overvalued consumer-facing winners.
3. They rotate into underpriced infrastructure providers that supply the primary
   narrative — picks-and-shovels plays.

**Why it's structurally predictable:** Infrastructure names are less "sexy",
carry lower analyst coverage, and often lag the primary narrative's initial run
by 6–18 months. This lag creates a persistent entry window.

**Historical analogue:** The late 1990s internet build-out. Telecom and
semiconductor equipment stocks continued rising even as internet companies' stock
prices stalled — JPMorgan's Jason Hunter labelled the divergence a market
"head fake" at the time. The same dynamic is now playing out in AI.

---

## The Stranded-Asset Pivot Pattern

Companies holding *stranded assets from a prior hype cycle* are systematic
candidates for the *next* cycle's infrastructure play. The asset base (power
capacity, datacenters, cooling) doesn't change — only the label changes.

**Observed examples (2025–2026):**
- Bitcoin miners (Galaxy Digital, Applied Digital, Cipher Mining, TeraWulf)
  pivoted to AI datacenter leasing. Their idled mining infrastructure — high-
  power density facilities with existing utility connections — maps directly onto
  hyperscaler datacenter requirements.
- TeraWulf signed a **20-year, ~$19B revenue** lease with Anthropic in August
  2026 for its Kentucky facility. Shares +93% YTD following the pivot.
- MicroStrategy / Strategy, unable to pivot a pure BTC treasury strategy to a
  productive asset, lost ~34% YTD as the stranded asset thesis failed.

**Key screening signal:** Look for companies with:
  - Existing high-density power infrastructure (>10 MW)
  - Manageable balance sheet debt
  - A prior hype-cycle identity that is actively dissolving
  - A credible operational pivot underway (not just announced)

---

## The AI Intra-Cycle Rotation Sequence

Based on observed analyst commentary (Morgan Stanley, JPMorgan, UBS, 2026),
the AI capital cycle appears to rotate through the following layers in sequence:

```
① Applications (ChatGPT, Alphabet, Meta)  ← early euphoria phase
        ↓
② Semiconductors (NVIDIA, TSMC, memory)   ← supply constraint phase
        ↓
③ Infrastructure (power utilities, cooling, datacenter REITs) ← bottleneck phase
        ↓
④ Hyperscalers (MSFT, AMZN, GOOGL, META)  ← monetisation phase
        ↓
⑤ Broadening (consumer discretionary, biotech, software re-rating)
```

**Current position (August 2026):** Rotation from ② to ③/④. Semis are down ~12%
from their June 2026 all-time high (Philadelphia Semiconductor Index). Morgan
Stanley's Mike Wilson recommends rotating from semis into hyperscalers. UBS
recommends semiconductor *equipment* as the next picks-and-shovels layer.

**The risk:** If ③ (infrastructure) stalls before ④ (hyperscalers) picks up, a
broader "risk-off" exit from the entire AI theme becomes possible (JPMorgan's
Jason Hunter scenario).

---

## Actionable Rules for the System

1. **Screen for stranded-asset pivots early.** When a prior hype cycle (crypto,
   AR/VR, NFTs, etc.) deflates, immediately scan for infrastructure companies
   whose physical assets (power, compute, cooling) are fungible with the *next*
   emerging theme's build-out requirements.

2. **Track intra-cycle rotation signals.** When the primary AI narrative stock
   (e.g., NVDA) enters a drawdown after a >50% run, shift UNCROWDED_TRADE bias
   toward the next rotation layer (infrastructure → hyperscalers).

3. **Treat JPMorgan "head fake" divergence as a warning.** When infrastructure
   stocks are rallying while primary AI stocks are flat/down, this is a fragile
   setup. If infrastructure momentum stalls, prepare for a full theme exit.

4. **Don't mistake rotation for collapse.** A correction in one rotation layer
   is not evidence the entire AI trade is over. Wilson (Morgan Stanley, 2026):
   "This is simply the next rotation — Semis to the Hyperscalers."

---

## Memory Ingestion & Formatting

- **Category & Prefix**: Stored under `UNCROWDED_TRADE` memory type in Supabase, but formatted for prompt context as `[THEMATIC FLOW]` to ensure the LLM interprets it as cycle-wide market context rather than a single-ticker trade tip.
- **Source of Truth**: Ingested via macro newsletters, consensus synthesis (`analysis/consensus.py`), or macro thesis seeding — NOT automatically generated from single-stock trade executions (to avoid memory pollution).
- **Decay Profile**: Decays at **0.72× per 30-day half-life** (~28%/month). Remains active across the 2–6 month rotation horizon and naturally drops below the `0.05` retrieval threshold by month 12.

---

## Related

- [[concepts/market-anomalies]] — Structural price distortions and factor premia
- [[concepts/memory-feedback]] — How UNCROWDED_TRADE memories are stored and retrieved
- [[concepts/ingestion]] — Newsletter scraping and market event ingestion
- [[sources/market-heuristics-source]] — Trading patterns and mental models
