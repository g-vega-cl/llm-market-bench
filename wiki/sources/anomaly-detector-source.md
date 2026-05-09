---
tags: [audit, code-quality, automation]
category: source
---

# Source: Anomaly Detector Design

Synthesized from `raw/docs/reference/anomaly-detector-design.md`.

## Takeaways

- **Two-Pass Audit Strategy**: Uses interface stubs for global context (Pass 1) and full source code for targeted analysis (Pass 2) to audit the project without hitting context limits.
- **Reproduction Engine**: For critical logic bugs, the detector attempts to generate a failing test case to prove the anomaly exists.
- **Static + Dynamic**: Combines code analysis with a Playwright-based crawler that verifies the live frontend for rendering errors or data hangs.
- **Suppression Fingerprinting**: Allows developers to silence known issues via a fingerprinting system that tracks specific file/error combinations.

## Related

- [[entities/engine]]
- [[entities/web-app]]
- [[entities/database]]
