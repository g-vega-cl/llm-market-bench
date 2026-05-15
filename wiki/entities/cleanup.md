---
tags: [database, maintenance, cleanup]
category: entity
---

# Database Cleanup

The database cleanup module (`core/cleanup.py`) provides a reusable, testable function for periodic database maintenance. It is invoked via the `cleanup` command in `main.py` and replaces the inline cleanup script previously embedded in the CI workflow.

## Operations

The `run_cleanup()` function performs three deletions:

1. **Ingestion logs** older than 48 hours
2. **Resolved/ignored system audits** older than 30 days
3. **Market feeling records** older than 30 days

## Usage

```sh
python main.py cleanup
```

## Related

- [[entities/engine]]
- [[concepts/observability-standard]]
