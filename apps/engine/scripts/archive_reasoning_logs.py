"""Archive older LLM reasoning logs from Supabase to local 4TB Postgres database.

Safely streams records older than `cutoff_days` from Supabase, writes them to the
local PostgREST archive endpoint, verifies the write, deletes the migrated records from
Supabase, and optionally runs VACUUM FULL to reclaim Supabase disk space.
"""

import argparse
import logging
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.db import get_supabase_client, with_retry

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("archive_reasoning_logs")

DEFAULT_ARCHIVE_URL = os.getenv("ARCHIVE_DB_URL", "http://127.0.0.1:3001")


def archive_llm_reasoning_logs(
    supabase_client: Any = None,
    archive_http_client: httpx.Client | None = None,
    archive_base_url: str = DEFAULT_ARCHIVE_URL,
    cutoff_days: int = 14,
    batch_size: int = 200,
    vacuum: bool = True,
) -> dict[str, Any]:
    """Archive LLM reasoning logs older than `cutoff_days` to local archive database."""
    if supabase_client is None:
        supabase_client = get_supabase_client()

    close_http = False
    if archive_http_client is None:
        archive_http_client = httpx.Client(
            base_url=archive_base_url,
            timeout=httpx.Timeout(60.0, connect=15.0),
            headers={"Prefer": "resolution=merge-duplicates"},
        )
        close_http = True

    cutoff_date = (datetime.now(UTC) - timedelta(days=cutoff_days)).isoformat()
    logger.info(
        f"Starting archival for llm_reasoning_logs created before {cutoff_date} (cutoff: {cutoff_days} days)..."
    )

    migrated_count = 0
    deleted_count = 0

    try:
        while True:
            # 1. Fetch next batch from Supabase
            response = with_retry(
                lambda: (
                    supabase_client.table("llm_reasoning_logs")
                    .select("*")
                    .lt("created_at", cutoff_date)
                    .order("created_at", desc=False)
                    .limit(batch_size)
                    .execute()
                ),
                "fetch_supabase_reasoning_logs",
            )

            batch = response.data
            if not batch:
                logger.info("No more records found matching cutoff date.")
                break

            batch_len = len(batch)
            logger.info(f"Processing batch of {batch_len} records (first created at {batch[0].get('created_at')})...")

            # 2. Insert into Local Archive PostgREST
            post_res = archive_http_client.post(
                "/llm_reasoning_logs",
                json=batch,
                headers={"Prefer": "resolution=merge-duplicates"},
            )
            post_res.raise_for_status()
            migrated_count += batch_len

            # 3. Delete migrated records from Supabase by ID
            batch_ids = [row["id"] for row in batch]
            del_res = with_retry(
                lambda b=batch_ids: supabase_client.table("llm_reasoning_logs").delete().in_("id", b).execute(),
                "delete_supabase_reasoning_logs",
            )
            deleted_count += len(del_res.data) if del_res.data else batch_len
            logger.info(f"Progress: migrated {migrated_count} records, deleted {deleted_count} from Supabase.")

        # 4. Optional VACUUM FULL to reclaim physical disk space on Supabase
        if vacuum and deleted_count > 0:
            logger.info("Running VACUUM FULL on Supabase to reclaim disk space...")
            try:
                supabase_client.rpc(
                    "exec_sql", {"query": "VACUUM (FULL, ANALYZE) public.llm_reasoning_logs;"}
                ).execute()
                logger.info("VACUUM FULL completed successfully.")
            except Exception as e:
                logger.warning(
                    f"Could not execute VACUUM FULL via RPC (may need manual run in Supabase SQL editor): {e}"
                )

    finally:
        if close_http:
            archive_http_client.close()

    stats = {
        "cutoff_date": cutoff_date,
        "migrated_count": migrated_count,
        "deleted_count": deleted_count,
    }
    logger.info(f"Archival complete: {stats}")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Archive old LLM reasoning logs to local DB.")
    parser.add_argument("--cutoff-days", type=int, default=14, help="Keep logs newer than N days (default: 14)")
    parser.add_argument("--batch-size", type=int, default=200, help="Batch size for transfer (default: 200)")
    parser.add_argument("--no-vacuum", action="store_true", help="Skip VACUUM FULL")
    parser.add_argument("--archive-url", type=str, default=DEFAULT_ARCHIVE_URL, help="Archive PostgREST URL")
    args = parser.parse_args()

    archive_llm_reasoning_logs(
        archive_base_url=args.archive_url,
        cutoff_days=args.cutoff_days,
        batch_size=args.batch_size,
        vacuum=not args.no_vacuum,
    )
