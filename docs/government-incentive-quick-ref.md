# Government Incentive Tracking - Quick Reference

## ✅ CAPTURE THESE (Market-Moving Nations)

### Approved Countries

**G7 (Always Capture)**
| Country | Key Agencies | Typical Policies |
|---------|-------------|------------------|
| 🇺🇸 United States | USDA, DoD, DOE, Treasury, SEC | Bills, Acts, Defense Production Act, tax credits |
| 🇬🇧 United Kingdom | HM Treasury, BEIS | Industrial strategy, green finance |
| 🇩🇪 Germany | BMWK, KfW | Energiewende, industrial subsidies |
| 🇫🇷 France | Bercy, ADEME | France 2030, nuclear policy |
| 🇮🇹 Italy | MEF, CDP | PNRR (EU recovery fund) |
| 🇨🇦 Canada | Finance Canada, EDC | Strategic Innovation Fund |
| 🇯🇵 Japan | MOF, METI | GX (Green Transformation), semiconductors |

**G20 Major Economies (Sector-Specific)**
| Country | Focus Areas |
|---------|-------------|
| 🇨🇳 China | Semiconductors, EVs, renewables, Made in China 2025 |
| 🇮🇳 India | PLI (Production Linked Incentives), digital infrastructure |
| 🇧🇷 Brazil | Agriculture, biofuels, Amazon development |
| 🇦🇺 Australia | Critical minerals, energy transition |
| 🇰🇷 South Korea | Semiconductors, batteries, displays |
| 🇲🇽 Mexico | Nearshoring, USMCA-related |
| 🇮🇩 Indonesia | Nickel, EV battery supply chain |
| 🇸🇦 Saudi Arabia | Vision 2030, oil policy, NEOM |
| 🇹🇷 Turkey | Earthquake recovery, inflation control |
| 🇦🇷 Argentina | IMF programs, lithium policy |
| 🇿🇦 South Africa | Energy crisis, mining policy |

**European Union**
- EU Commission directives
- European Green Deal
- CBAM (Carbon Border Adjustment)
- NextGenerationEU funds

**Other Market-Movers**
| Country | Focus |
|---------|-------|
| 🇨🇭 Switzerland | Financial regulation, pharma |
| 🇸🇬 Singapore | Financial hub, biotech |
| 🇮🇱 Israel | Defense tech, startups |
| 🇦🇪 UAE | Oil policy (OPEC+), diversification |

---

## ✅ CAPTURE THESE (Policy Types)

### Legislative Actions
- [ ] Bills passed by legislature
- [ ] Bills advancing through committees
- [ ] Multi-party supported legislation
- [ ] Budget reconciliation bills

### Budget & Spending
- [ ] Appropriations bills
- [ ] Multi-year budget frameworks
- [ ] Emergency spending packages
- [ ] Sovereign wealth fund allocations

### Subsidies & Incentives
- [ ] Tax credits (ITC, PTC, R&D)
- [ ] Direct subsidies/grants
- [ ] Loan guarantees
- [ ] Cost-sharing programs (e.g., 90% coverage)
- [ ] Production incentives

### Regulatory Changes
- [ ] New regulations with compliance costs
- [ ] Deregulation initiatives
- [ ] Trade policies (tariffs, quotas)
- [ ] Export/import restrictions
- [ ] Environmental mandates

### Policy Objectives (With Funding)
- [ ] Net-zero targets with budget attached
- [ ] Technology adoption goals (e.g., 50% EVs by 2030)
- [ ] Self-sufficiency plans (e.g., chips, pharma)
- [ ] Infrastructure targets

### Agency Actions
- [ ] Defense Production Act invocation
- [ ] Fast-track approval pathways
- [ ] Strategic procurement contracts
- [ ] Emergency authorities used

---

## ❌ IGNORE THESE (Noise)

### Political Theater
- [ ] Campaign promises (no legislative path)
- [ ] Party platform documents
- [ ] Speeches without policy details
- [ ] Election manifestos (pre-election)

### Too Local/Minor
- [ ] Municipal ordinances (unless NYC, London, Tokyo finance)
- [ ] State/provincial policies (unless CA, TX, Bavaria-level impact)
- [ ] Minor regulatory tweaks
- [ ] Permit approvals (routine)

### No Funding/Teeth
- [ ] Study commissions
- [ ] Task force announcements
- [ ] "Exploring" or "considering" policies
- [ ] Non-binding resolutions

### Wrong Countries
- [ ] Small economies (unless OPEC/resource-critical)
- [ ] Sanctioned nations (Iran, North Korea, Russia)
- [ ] Countries in the approved list above

---

## 📊 Importance Score Guide

### Score 8-10 (Economy-Wide Impact)
**Examples:**
- US Farm Bill with $50B+ funding
- EU Green Deal Industrial Plan
- China semiconductor independence ($200B+)
- Defense Production Act for critical sectors

**Criteria:**
- ✓ Billions in funding
- ✓ Multiple sectors affected
- ✓ Multi-year duration
- ✓ Market-moving potential

### Score 5-7 (Sector-Specific Impact)
**Examples:**
- Solar ITC extension
- EV tax credits
- Biotech R&D grants
- Sector-specific deregulation

**Criteria:**
- ✓ Hundreds of millions to low billions
- ✓ Single sector or technology
- ✓ Clear beneficiaries
- ✓ Moderate market impact

### Score 1-4 (Narrow Impact)
**Examples:**
- Regional development grants
- Small business tax incentives
- Pilot programs
- Research funding for specific tech

**Criteria:**
- ✓ Under $100M
- ✓ Narrow scope
- ✓ Limited market impact
- ✓ Mostly symbolic

---

## 🎯 Metadata Checklist

When capturing government incentives:

```python
{
    "event_name": "Clear, concise name (e.g., 'US Farm Bill 2026 Agri-Tech Push')",
    "impact": "BULLISH" | "BEARISH" | "NEUTRAL",
    "is_government_incentive": True,  # REQUIRED
    "expiry_date": "YYYY" | "YYYY-MM-DD" | None,  # If mentioned
    "importance_score": 1-10,  # Based on guide above
    "is_ongoing": True | False,  # Ongoing implementation?
    "is_future_catalyst": True | False,  # Pending vote/decision?
    "scenario_analysis": """
        Scenario A: [Passes as-is] -> Trading Plan: [Specific assets]
        Scenario B: [Watered down] -> Trading Plan: [Specific assets]
    """,  # REQUIRED for uncertain outcomes
    "source_id": "newsletter_chunk_id"
}
```

---

## 🔍 Keyword Triggers

Use these to detect government incentive content:

**Legislative:**
- bill, act, law, legislation, congress, parliament, diet, bundestag
- passed, advanced, committee, vote, ratify

**Financial:**
- budget, appropriation, allocation, funding, spending
- subsidy, grant, incentive, tax credit, deduction
- loan guarantee, cost-sharing, reimbursement

**Policy:**
- policy, regulation, directive, rule, mandate
- executive order, proclamation, decree
- strategy, plan, initiative, program

**Agencies:**
- usda, dod, doe, treasury, sec, fda, epa
- moody, meti, mof (Japan)
- ndrc, miit (China)
- ec, ecb (EU)

**Emergency Powers:**
- defense production act, national emergency
- invocation, invoke, emergency powers

---

## 📝 Example Classifications

### Example 1: US Farm Bill 2026
```
News: "Congress advances Farm, Food and National Security Act of 2026 with 
90% cost coverage for precision agriculture"

✅ CAPTURE: Major legislation, sector-specific
Event Name: "US Farm Bill 2026 Agri-Tech Push"
is_government_incentive: true
importance_score: 8
expiry_date: "2031" (5-year farm bill typical)
```

### Example 2: EU Green Hydrogen Act
```
News: "EU approves €30B Green Hydrogen Acceleration Act"

✅ CAPTURE: Multi-billion EU legislation
Event Name: "EU Green Hydrogen Acceleration Act"
is_government_incentive: true
importance_score: 7
expiry_date: "2030"
```

### Example 3: Senator Proposes Study
```
News: "Senator introduces bill to study EV adoption barriers"

❌ IGNORE: No funding, just a study
Reason: Study commission, no market impact
```

### Example 4: Mayor Announces Local Program
```
News: "Paris Mayor announces €10M EV charging expansion"

❌ IGNORE: Municipal level, too small
Reason: Local policy, not national
```

---

## 🚨 Enforcement Rules

**HARD REQUIREMENT:**
> If news contains government legislation/budget/subsidy/policy from approved countries → MUST generate macro_event with `is_government_incentive=true`

**Validation Warnings:**
1. Government content detected + NO macro_events → ⚠️ Warning
2. Government content detected + no `is_government_incentive=true` → ⚠️ Warning
3. Macro event generated but missing metadata → ⚠️ Warning

**Audit Trail:**
All warnings logged to: `GOVERNMENT INCENTIVE ENFORCEMENT`
