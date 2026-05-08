---
tags: [source, anomaly, detection, audit]
category: source
source: docs/reference/anomaly-detector-design.md
---

# Source: Code Anomaly Detection Agent

Automated LLM-powered scanner that continuously audits the codebase and live website.

Key details:

- **5 scan types**: Code & logic analysis, doc-code consistency, cross-module dependency, live website crawl, comprehensive reporting
- **Two-Pass Context Strategy**: Pass 1 extracts interface stubs across project, Pass 2 analyzes specific groups with those stubs as context
- **Reproduction Engine**: generates Vitest/Pytest test cases to verify High/Critical findings (only promotes if test actually fails)
- **Website Crawl**: Playwright-based, checks for broken links, React errors, hydration mismatches, stale data
- **Suppression**: fingerprint-based `anomalies.ignore.json` with optional expiry
- **Execution**: CLI (`python -m anomaly_detector`) or scheduled (GitHub Actions, off-market hours)
- **Success criteria**: <10% false positive rate for Critical, >80% injected defect detection
