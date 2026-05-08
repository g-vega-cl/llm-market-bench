---
tags: [source, pipeline, data-flow]
category: source
source: docs/engine/data-flow.md
---

# Source: Data Flow & Pipeline Reference

Complete walkthrough of the daily pipeline. Covered in [[entities/pipeline]].

Key details from this source:

- Six-phase pipeline: Ingestion → Pre-Analysis → Analysis → Consensus → Execution → Feedback
- Deterministic `source_id` = `date + sender + subject → MD5[:8]`
- Batch strategy: chunks split to avoid truncation, each batch gets full context
- 3-attempt retry loop with corrective prompting for structured extraction
- "Commit at the End" atomic settlement pattern prevents phantom deductions
- Manager Agent multi-horizon (short, medium, long) post-mortem intervals
- Cause & Effect: semantic dedup, dynamic ticker discovery via Gemini, causal attribution
