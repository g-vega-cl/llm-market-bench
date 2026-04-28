# Government Incentive Prompt Enhancement

## Status: Implemented & Verified ✅

> [!NOTE]
> These requirements have been consolidated into the unified `CORE_ANALYSIS_SYSTEM_PROMPT` in `llm-market-bench/apps/engine/core/llm/prompts.py`. This ensures that all models (not just Claude/OpenAI) adhere to the government incentive and macro-event criteria.

### CORE_ANALYSIS_SYSTEM_PROMPT Integration
The unified prompt now automatically includes the logic to enforce tool verification before trades and to identify government policy content for macro-event generation.

This enhancement addresses a critical gap in the LLM analysis pipeline: **failure to capture government policy changes as macro events**.

### Problem Identified

During the March 17, 2026 Farm Bill analysis:
- ✅ Newsletter was successfully ingested
- ✅ LLMs generated trading decisions (DE BUY signals)
- ❌ **No macro events were created** for the Farm Bill legislation
- ❌ **No memory was stored** in the consensus protocol

**Root Cause**: LLMs prioritized trading decisions over macro event generation, treating government policy as trade rationale rather than a standalone market-moving event.

---

## Solution: Enhanced Government Incentive Tracking

### What Changed

#### 1. **Prompt Enhancement** (`core/llm/prompts.py`)

Added a comprehensive **GOVERNMENT INCENTIVES & POLICY TRACKING** section with:

##### Scope Definition (Noise Filtering)
Only captures policies from economically powerful nations:
- **G7 Countries**: US, UK, Germany, France, Italy, Canada, Japan
- **G20 Major Economies**: China, India, Brazil, Australia, South Korea, Mexico, Indonesia, Saudi Arabia, Turkey, Argentina, South Africa
- **EU Institutions**
- **Other Market-Movers**: Switzerland, Singapore, Israel, UAE (energy/finance-specific)

##### What to Capture
- Legislative bills (e.g., "Farm, Food and National Security Act of 2026")
- Budget allocations (e.g., "$50B for semiconductor manufacturing")
- Regulatory changes (e.g., tariff removals, export restrictions)
- Government incentives (tax credits, subsidies, grants)
- Policy objectives with funding (e.g., "net-zero by 2030 with $100B")
- Agency actions (e.g., "FDA fast-track approval", "DoD procurement")

##### What to Ignore (Noise Filtering)
- Campaign promises without legislative progress
- Minor regulatory tweaks with no market impact
- Local/municipal policies (unless mega-cities like NYC, London, Tokyo)
- Non-approved countries (unless OPEC-level impact)
- Vague political rhetoric without concrete action

##### Metadata Requirements
- `is_government_incentive = true`
- `expiry_date` if mentioned (e.g., "2027" for budget year)
- `importance_score` based on:
  - **8-10**: Major legislation with billions, economy-wide impact
  - **5-7**: Sector-specific incentives, meaningful budget
  - **1-4**: Narrow programs, limited impact

##### Examples Provided
**GOOD (Capture these)**:
- "US Congress advances Farm Bill with $50B for precision agriculture subsidies"
- "EU approves €30B Green Hydrogen Acceleration Act"
- "China announces 10-year semiconductor self-sufficiency plan with $200B fund"

**IGNORE (Noise)**:
- "Senator proposes idea for infrastructure bill" (no progress)
- "Mayor of Paris announces local EV subsidy" (municipal)
- "Political party campaign promise for tax cuts" (no funding)

##### Mandatory Enforcement
> **If ANY news snippet mentions government legislation, budgets, subsidies, or policy changes from the approved countries above, you MUST generate at least ONE macro event with 'is_government_incentive' = true.**

---

#### 2. **Runtime Validation & Policy Lookup** (`core/llm/analysis.py`)

Added post-analysis validation that **rejects vague government events** instead of injecting generic fallbacks:

1. **Scans news chunks** for government-related keywords:
   - "bill", "act", "congress", "parliament", "legislation"
   - "subsidy", "grant", "incentive", "budget", "funding"
   - "tax credit", "policy", "regulation", "directive"
   - "executive order", "defense production act"
   - "usda", "dod", "doe", "sec", "treasury", "federal"

2. **Detects vague government events** — any macro event with `is_government_incentive=true` whose `event_name` matches generic patterns like "Government Policy Update", "Ongoing Legislative Policy Developments", etc.

3. **Attempts policy enrichment** via `core/llm/policy_lookup.py`:
   - Calls Gemini with **Google Search** to identify the specific bill/act/regulation name, current status, and description from the chunk content.
   - If found (confidence ≥ 50) → enriches the event: `"CHIPS and Science Act [passed Senate]"` with a detailed description.
   - If not found → **removes the vague event entirely** (no generic placeholder).

4. **Logs warnings** when government content is present but no specific macro event was identified or flagged.

#### 3. **Consensus Gate** (`consensus.py`)

Added a safety net in the consensus synthesis pipeline:
- After LLM synthesis, checks if the synthesized event name is a vague government event (matching generic patterns).
- If vague → **rejects and does NOT promote to memory**.
- If specific → promotes normally.

This ensures that no vague government event makes it into long-term memory, even if the analysis stage somehow misses it.

#### 4. **Prompt Specificity Enforcement** (`core/llm/prompts.py`)

Both the **analysis prompt** (`ANALYSIS_USER_PROMPT_TEMPLATE`) and the **synthesis prompt** (`SYNTHESIS_USER_PROMPT_TEMPLATE`) now include hard specificity requirements:

- *"Government event names MUST include the specific bill, act, or regulation. Generic names like 'Government Policy Update' are INVALID and will be rejected."*
- *"If raw inputs are too vague to name a specific policy, set 'name' to 'VAGUE_GOVERNMENT_EVENT' and the system will reject it."*

---

## Expected Impact

### Before Enhancement (Fallback Injection)
```
Newsletter: Farm Bill 2026
├── Decisions: DE BUY (2 models)
├── Macro Events: ["Government Policy Update" (vague)] ← INJECTED FALLBACK
└── Memory: "Ongoing Legislative Policy Developments" ← MEANINGLESS
```

### After Enhancement (Specificity + Lookup)
```
Newsletter: Farm Bill 2026
├── Decisions: DE BUY (all models)
├── Macro Events: ["US Farm Bill 2026 Agri-Tech Push" (specific)] ← MODEL OR LOOKUP
└── Memory: "US Farm Bill 2026 [in committee]" ← ACTIONABLE
```

If the policy cannot be identified:
```
Newsletter: Vague policy mention
├── Model returns: "Government Policy Update" (vague) 
├── Policy Lookup: No specific policy found
└── Result: Event REMOVED ← No worthless memory
```

---

## Testing Strategy

### Automated Tests
```bash
# Tool enforcement + government validation tests (11 tests)
python -m pytest tests/test_tool_enforcement.py -v

# Consensus gate + vague event rejection tests (27 tests)
python -m pytest tests/test_consensus.py -v
```

**Key test coverage**:
- `test_validate_and_enrich_removes_vague_government_event` — Vague event removed when lookup fails
- `test_validate_and_enrich_preserves_specific_event` — Specific event preserved unchanged
- `test_validate_and_enrich_enriches_vague_event_on_lookup_success` — Policy lookup enriches vague event with name + status
- `test_is_vague_government_event_true_for_generic_names` — Consensus helper flags 6 generic patterns
- `test_process_consensus_rejects_vague_government_event` — Consensus pipeline rejects vague events
- `test_process_consensus_accepts_specific_government_event` — Consensus pipeline accepts specific events

### Monitoring
During pipeline runs, watch logs for:
1. ✅ "ENRICHED GOVERNMENT EVENT" — policy lookup identified a specific policy
2. ⚠️ "REMOVING VAGUE GOVERNMENT EVENT" — vague event removed (no policy found)
3. ⚠️ "Rejecting vague government event from consensus" — consensus gate caught a slip-through

---

## Related Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `core/llm/prompts.py` | Added Government Incentives section + specificity enforcement | Guide LLMs; reject generic names |
| `core/llm/analysis.py` | Replaced `_ensure_government_incentive_events` with `_validate_and_enrich_government_events` | Reject vague events; enrich via policy lookup |
| `core/llm/policy_lookup.py` | **NEW** — Gemini + Google Search policy identification | Find specific bill/act/regulation names |
| `consensus.py` | Added `_is_vague_government_event` + rejection gate | Safety net: reject vague events before memory promotion |
| `tests/test_tool_enforcement.py` | 11 tests (3 new: validate+enrich, 3 old removed) | Coverage for analysis-stage validation |
| `tests/test_consensus.py` | 27 tests (17 new: gate + parametric helper tests) | Coverage for consensus-stage rejection |

---

## Future Enhancements

1. **Lower Consensus Threshold** for government incentives (2.0 → 1.5)
   - Ensure single-model detection can still capture major policies

2. **Automatic Memory Bypass** for government incentives
   - Skip consensus protocol for `is_government_incentive=true` events
   - Direct insertion with lower similarity threshold

3. **Government Policy Dashboard**
   - Dedicated view for tracking active incentives by country/sector
   - Expiry date alerts for sunset provisions

4. **Historical Policy Database**
   - Track policy success/failure rates
   - Train LLMs on historical policy market impacts

---

## References

- Root Cause Analysis: `apps/engine/root_cause_farm_bill.py`
- Consensus Protocol: `apps/engine/consensus.py`
- Memory Store: `apps/engine/memory/store.py`
- Original Issue: Farm Bill newsletter (March 17, 2026)
