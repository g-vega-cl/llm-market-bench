# Government Incentive Prompt Enhancement

## Overview

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

#### 2. **Runtime Validation** (`core/llm/analysis.py`)

Added post-analysis validation that:

1. **Scans news chunks** for government-related keywords:
   - "bill", "act", "congress", "parliament", "legislation"
   - "subsidy", "grant", "incentive", "budget", "funding"
   - "tax credit", "policy", "regulation", "directive"
   - "executive order", "defense production act"
   - "usda", "dod", "doe", "sec", "treasury", "federal"

2. **Validates macro event generation**:
   - If government content detected but NO macro events → Warning logged
   - If government content detected but no `is_government_incentive=true` event → Warning logged

3. **Provides audit trail** for prompt compliance monitoring

---

## Expected Impact

### Before Enhancement
```
Newsletter: Farm Bill 2026
├── Decisions: DE BUY (2 models)
├── Macro Events: [] ← EMPTY
└── Memory: NOT CREATED ❌
```

### After Enhancement
```
Newsletter: Farm Bill 2026
├── Decisions: DE BUY (all models)
├── Macro Events: [
│   "US Farm Bill 2026 Agri-Tech Push" (is_government_incentive=true)
│   ]
└── Memory: CREATED ✅ (via consensus protocol)
```

---

## Testing Strategy

### Next Pipeline Run
Monitor logs for:
1. ✅ Macro events generated with `is_government_incentive=true`
2. ✅ No "GOVERNMENT INCENTIVE ENFORCEMENT" warnings
3. ✅ Consensus protocol promotes government events to memory
4. ✅ Dashboard shows new GOVERNMENT_INCENTIVE memories

### Validation Queries
```python
# Check for government incentive memories
client.table("memories").select("*").eq("memory_type", "GOVERNMENT_INCENTIVE").execute()

# Check for enforcement warnings in logs
grep "GOVERNMENT INCENTIVE ENFORCEMENT" logs/
```

---

## Related Files Modified

| File | Change | Purpose |
|------|--------|---------|
| `core/llm/prompts.py` | Added Government Incentives section | Guide LLMs to capture policy events |
| `core/llm/prompts.py` | Added examples (GOOD/IGNORE) | Concrete guidance for LLMs |
| `core/llm/prompts.py` | Added mandatory enforcement rule | Hard requirement for compliance |
| `core/llm/analysis.py` | Added runtime validation | Audit trail for prompt compliance |

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
