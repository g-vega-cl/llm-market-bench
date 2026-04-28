# Code Anomaly Detection Agent - Design Document

## 1. Why We Need This

The AI Wall Street project is a complex, multi-LLM trading platform with:
- A **Python data engine** handling LLM calls, trade validation, portfolio management, and financial calculations
- A **TypeScript web dashboard** rendering real-time portfolio data, trade audit trails, and AI cognitive synthesis
- **Infrastructure config** (Supabase migrations, GitHub Actions, environment variables)
- **Extensive documentation** describing how each component should work

As the codebase evolves, several risks emerge:
1. **Code rot**: Changes in one module silently break assumptions in dependent modules
2. **Doc drift**: Documentation becomes outdated as implementation changes
3. **Performance degradation**: Inefficient patterns creep in (N+1 queries, missing caching, redundant API calls)
4. **Live UI regressions**: Deployed dashboard pages may have broken links, rendering issues, or data mismatches
5. **Config inconsistencies**: Environment variables, rate limits, or scheduled tasks become misconfigured

Manual code reviews catch some of these, but not systematically or at scale. We need an **automated, LLM-powered anomaly detector** that continuously audits the entire codebase and live website, producing comprehensive reports that developers can act on.

---

## 2. What This Agent Does

An automated scanning agent that:

### A. Code & Logic Analysis
- Scans Python engine code for **logic bugs, edge cases, error handling gaps, and incorrect assumptions**
- Analyzes TypeScript web code for **state management issues, data fetching anti-patterns, rendering bugs**
- Detects **performance issues**: N+1 queries, missing batching, redundant API calls, memory leaks
- **Logic Validation**: For High/Critical logic findings, the agent attempts to generate a **reproduction script** (Vitest/Pytest) to confirm the bug is real and not an LLM hallucination.

### B. Documentation-to-Code Consistency
- Compares documentation claims (in `docs/*.md`) against actual implementation
- **Structured Constraints**: Audits code against measurable assertions defined in documentation (e.g., YAML frontmatter blocks defining TTLs, rate limits, or architectural rules).
- Identifies undocumented features or deprecated functionality still referenced in docs

### C. Cross-Module Dependency Analysis
- **Two-Pass Context Strategy**: 
    1.  **Pass 1**: Extracts interfaces and signatures (stubs) for the entire project.
    2.  **Pass 2**: Analyzes specific logic groups using those stubs as lightweight context to prevent token exhaustion and "God Object" context bloating.
- Analyzes each group for **cross-file inconsistencies** (e.g., function signatures that changed but callers weren't updated).

### D. Live Website Crawl (Dynamic)
- Crawls all **public (unauthenticated) pages** on `https://benchify.netlify.app` using **Playwright** to ensure full JavaScript execution. Authenticated routes (e.g., comments, admin tools) are out of scope.
- Checks for **broken links, React rendering errors, hydration mismatches, and data hangs**.
- Validates that **live data matches expected formats** (e.g., portfolio tables render, trade feed populates).
- Compares deployed UI against documentation claims (e.g., does the "Consensus Meter" actually exist in the DOM?).

### E. Comprehensive Reporting
- Generates **detailed markdown reports** with:
  - **Anomaly description** and severity (Critical / High / Medium / Low / Info)
  - **Affected files** with line numbers and code snippets
  - **Suppression Mechanism**: Uses **fingerprinting** (hash of file path + error type + context) to allow developers to "silence" known issues via an `anomalies.ignore.json` file.
  - **Root cause analysis** and **Suggested fix** with code examples.
  - **Reproduction Proof**: Links to generated test cases for validated critical bugs.

---

## 3. Architecture

```
apps/engine/anomaly_detector/
├── __init__.py
├── cli.py                    # CLI entry point for manual execution
├── config.py                 # Agent configuration (Market Hours awareness, API quotas)
├── core/
│   ├── __init__.py
│   ├── llm_client.py         # DeepSeek API client (reuses project .env keys)
│   ├── file_loader.py        # Loads files with smart chunking and stub generation
│   ├── dependency_graph.py   # Builds import dependency graph to group files
│   └── prompt_templates.py   # System prompts for different scan types
├── scanners/
│   ├── __init__.py
│   ├── code_scanner.py       # Analyzes code groups for logic/perf/security issues
│   ├── doc_scanner.py        # Compares documentation against implementation
│   ├── infra_scanner.py      # Validates config, env vars, and LIVE DB schema drift
│   └── performance_scanner.py # Static analysis for N+1 queries, redundant calls, etc.
├── reproduction_engine/
│   ├── __init__.py
│   ├── test_generator.py     # Generates Vitest/Pytest reproduction cases
│   └── validator.py          # Executes generated tests via subprocess to confirm findings
├── crawler/
│   ├── __init__.py
│   ├── playwright_client.py  # Headless browser client for JS-heavy pages
│   ├── site_crawler.py       # Crawls public pages, checks links, validates UI
│   └── ui_validator.py       # Compares live UI against documentation claims
├── reporters/
│   ├── __init__.py
│   ├── suppression_manager.py # Handles fingerprinting and ignore lists
│   ├── report_generator.py   # Generates comprehensive markdown reports
│   └── severity_classifier.py # Classifies findings by severity and category
└── main.py                   # Orchestrates the full scan pipeline
```

---

## 4. How It Works (Pipeline)

### Phase 1: Discovery & Grouping
1. **Build dependency graph**: Parse all Python `.py` and TypeScript `.ts/.tsx` files.
2. **Interface Extraction (Pass 1)**: Generate lightweight stubs for all files to use as global context.
3. **Group by dependencies**: Cluster related files into analysis groups that fit within LLM context windows.
4. **Load documentation assertions**: Index `docs/*.md` and extract structured YAML/JSON constraints.

### Phase 2: Scanning (Parallel)
5. **Code scan** (per dependency group):
   - Send grouped file contents + global stubs to DeepSeek.
   - For High/Critical findings, trigger the **Reproduction Engine** to attempt creating a failing test case.
   - **Validation**: The `validator.py` runs generated tests via `subprocess.run(['pytest', test_file])` and only promotes a finding to **"Verified"** if the process exits with code 1 (actual test failure). This prevents LLM-hallucinated proofs.
6. **Infrastructure & DB Drift scan**:
   - Compare ORM definitions to **live database schema** (via `information_schema`).
   - Validate `.env` variables and GitHub Actions workflows.
7. **Documentation consistency scan**:
   - Verify code adheres to the structured assertions extracted in Phase 1.
8. **Website crawl** (headless):
   - Launch Playwright to fetch all routes.
   - Wait for hydration; check for React errors and "Empty State" hangs.

### Phase 3: Synthesis & Reporting
9.  **Deduplicate & Suppress**: Merge similar issues and filter out findings matching fingerprints in `anomalies.ignore.json`.
10. **Classify severity**: Critical / High / Medium / Low / Info.
11. **Generate markdown report**: Structured report with reproduction proofs and suggested fixes.

---

## 5. LLM Integration

### Provider: DeepSeek (cheapest option)
- Model: `deepseek-v4-flash` (thinking mode for complex analysis).
- Context window: 64K tokens.

### Token Management (The Two-Pass Strategy)
To avoid context exhaustion in large projects:
- **Global Context**: The LLM receives a "Project Summary" containing the interface stubs of all files (Pass 1).
- **Local Context**: The LLM receives the full source code for only the specific dependency group being analyzed (Pass 2).
- This ensures the LLM knows *what* other functions exist without needing to read their full implementation.

---

## 6. Execution Modes

### Manual (CLI)
```bash
python -m anomaly_detector --scan code --validate  # Run scan + reproduction tests
```

### Scheduled (GitHub Actions)
- **Trigger**: Runs on a dedicated workflow (`.github/workflows/anomaly_scan.yml`) on weekday off-market hours:
  ```yaml
  on:
    schedule:
      - cron: '0 3 * * 1-5'  # 03:00 UTC (22:00 ET), weekdays only
  ```
- **Quota Guard**: Reuses the project's `DEEPSEEK_API_KEY` secret. Add to GitHub → Settings → Secrets.

---

## 7. Website Crawl Details

### Crawl Implementation
- **Tech**: **Playwright** (Python).
- **Scope**: Unauthenticated public routes only. Authenticated features (e.g., comments, user sessions) are out of scope.
- **Logic**: 
    1.  Initialize headless browser.
    2.  Navigate to page and `wait_for_selector()` on a known anchor element (e.g., the Market Status Hero banner). Using `wait_until="networkidle"` is avoided because TanStack Query's background refetching prevents the page from ever reaching a true network-idle state.
    3.  Check browser console for JavaScript errors or failed network requests (4xx/5xx).
    4.  Extract the **Rendered DOM** and compare against documentation-defined UI components.
    5.  Check for **Stale Data** only during market hours (09:30–16:00 ET, via the FMP market status API): flag if the "Last Updated" timestamp is more than 2 hours old. Suppress this check outside market hours, as overnight data staleness is expected.

---

## 8. Report Format (Updated)

```markdown
## Critical Findings

### [C-001] Race Condition in Portfolio Settlement
**Severity**: Critical
**Proof**: ✅ Verified via `subprocess.run(['pytest', 'tests/repro_c001.py'])` → exit code 1 (Failed in 120ms)
**Files**: `apps/engine/execution/portfolio.py:247`
**Description**: Concurrent `execute_trade` calls lead to negative balances.
...
```

---

## 8.5 Suppression File Format

Developers can silence known issues by adding entries to `anomalies.ignore.json`:

```json
{
  "suppressions": [
    {
      "fingerprint": "a3f1c2b9",
      "reason": "Known issue — tracked in GitHub #42",
      "added_by": "your-github-handle",
      "expires": "2026-06-01"
    }
  ]
}
```

The `fingerprint` is a hash of `file_path + error_type + context_snippet`, printed in every report. The `expires` field is optional; after this date the suppression is automatically re-activated.

---

## 9. Implementation Phases

### Phase 1: Core & Two-Pass Logic
- Interface extractor (Stub generator).
- Dependency graph builder.
- Fingerprinting and suppression engine.

### Phase 2: Dynamic Scanning
- Playwright-based website crawler.
- Live DB schema auditor (Postgres `information_schema`).
- Reproduction engine (LLM-driven test generation).

### Phase 3: Integration
- Market-hours aware CI/CD workflow.
- Doc-assertion parser (YAML frontmatter).

---

## 10. Success Criteria

1. **Noise Reduction (Precision)**: <10% false positive rate for "Critical" findings due to reproduction validation.
2. **Detection Coverage (Recall)**: A canary suite of known bugs (seeded into test branches) is used to verify that at least 80% of injected defects are caught per scan run.
3. **Deep Reach**: Successfully detects bugs in JS-rendered UI components.
4. **Infrastructure Safety**: Zero impact on production API quotas during market hours.
5. **Consistency**: 100% of architectural claims in docs are audited against code.
