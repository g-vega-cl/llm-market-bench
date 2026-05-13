import logging
from datetime import UTC, datetime, timedelta

from supabase import create_client

from .analyzer import analyze_log_blob
from .checks import AUDIT_CHECKS

logger = logging.getLogger("engine")

SUPABASE_URL = None
SUPABASE_SERVICE_ROLE_KEY = None

def configure(url: str, service_role_key: str):
    global SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    SUPABASE_URL = url
    SUPABASE_SERVICE_ROLE_KEY = service_role_key


def generate_audit_run_id() -> str:
    return datetime.now(UTC).strftime("audit-%Y%m%d-%H%M%S")


async def run_audit():
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Supabase not configured for audit")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    audit_run_id = generate_audit_run_id()

    logger.info(f"Starting audit run: {audit_run_id}")

    sql_finding_count = 0
    for check in AUDIT_CHECKS:
        try:
            result = supabase.rpc(
                "exec_sql",
                {"query": check["query"].strip()}
            ).execute()

            if result.data:
                for row in result.data:
                    row_data = row.get("result", row)
                    insert_audit(
                        supabase,
                        audit_run_id=audit_run_id,
                        check=check,
                        source_id=row_data.get("id"),
                        metadata=row_data
                    )
                    sql_finding_count += 1
                logger.info(f"Check '{check['id']}': found {len(result.data)} issues")
            else:
                logger.debug(f"Check '{check['id']}': no issues found")

        except Exception as e:
            logger.error(f"Check '{check['id']}' failed: {e}")

    logger.info(f"SQL checks complete: {sql_finding_count} findings")

    log_finding_count = await analyze_recent_logs(supabase, audit_run_id)
    logger.info(f"Log analysis complete: {log_finding_count} findings")

    logger.info(f"Audit run {audit_run_id} complete")


def insert_audit(
    supabase,
    audit_run_id: str,
    check: dict,
    source_id,
    metadata: dict
):
    audit = {
        "audit_type": categorize_audit_type(check["id"]),
        "severity": check["severity"],
        "title": check["title"],
        "description": f"{check['description']}. Found: {metadata}",
        "status": "OPEN",
        "source_table": check["source_table"],
        "source_id": source_id,
        "metadata": metadata,
        "audit_run_id": audit_run_id,
        "analysis_method": check["analysis_method"],
        "created_by": "SYSTEM"
    }

    supabase.table("system_audits").insert(audit).execute()


def categorize_audit_type(check_id: str) -> str:
    if check_id.startswith("orphan") or check_id.startswith("executed"):
        return "DB_ANOMALY"
    elif check_id.startswith("invalid") or check_id.startswith("stale") or check_id.startswith("empty") or check_id.startswith("duplicate"):
        return "DATA_QUALITY"
    else:
        return "CODE_ERROR"


async def analyze_recent_logs(supabase, audit_run_id: str):
    cutoff = datetime.now(UTC) - timedelta(hours=48)
    cutoff_str = cutoff.isoformat()

    result = supabase.table("ingestion_logs") \
        .select("*") \
        .gte("created_at", cutoff_str) \
        .order("created_at", desc=True) \
        .execute()

    if not result.data:
        logger.info("No recent ingestion logs found for analysis")
        return 0

    logs_combined = "\n".join([
        f"=== Run: {log['run_id']} ({log['run_date']}) ===\n{log['log_blob']}"
        for log in result.data
    ])

    suggestions = await analyze_log_blob(logs_combined)

    if suggestions:
        insert_log_audit(
            supabase,
            audit_run_id=audit_run_id,
            description=f"Analyzed {len(result.data)} ingestion logs from past 48 hours",
            suggestions=suggestions
        )
        return 1

    return 0


def insert_log_audit(
    supabase,
    audit_run_id: str,
    description: str,
    suggestions: str
):
    audit = {
        "audit_type": "SYSTEM_LOG",
        "severity": "MEDIUM",
        "title": "System Log Analysis",
        "description": description,
        "suggestion": suggestions,
        "status": "OPEN",
        "audit_run_id": audit_run_id,
        "analysis_method": "LLM_ANALYSIS",
        "created_by": "SYSTEM"
    }

    supabase.table("system_audits").insert(audit).execute()