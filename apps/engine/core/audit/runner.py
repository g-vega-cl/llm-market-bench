import json
import logging
import os
import random
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


async def run_audit(dry_run: bool = False):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.error("Supabase not configured for audit")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    audit_run_id = generate_audit_run_id()

    prefix = "[DRY RUN] " if dry_run else ""
    logger.info(f"{prefix}Starting audit run: {audit_run_id}")

    sql_finding_count = 0
    for check in AUDIT_CHECKS:
        try:
            result = supabase.rpc("exec_sql", {"query": check["query"].strip()}).execute()

            if result.data:
                for row in result.data:
                    row_data = row.get("result", row)
                    insert_audit(
                        supabase,
                        audit_run_id=audit_run_id,
                        check=check,
                        source_id=row_data.get("id"),
                        metadata=row_data,
                        dry_run=dry_run,
                    )
                    sql_finding_count += 1
                logger.info(f"Check '{check['id']}': found {len(result.data)} issues")
            else:
                logger.debug(f"Check '{check['id']}': no issues found")

        except Exception as e:
            logger.error(f"Check '{check['id']}' failed: {e}")

    logger.info(f"SQL checks complete: {sql_finding_count} findings")

    log_finding_count = await analyze_recent_logs(supabase, audit_run_id, dry_run=dry_run)
    logger.info(f"Log analysis complete: {log_finding_count} findings")

    logger.info(f"{prefix}Audit run {audit_run_id} complete")


def insert_audit(supabase, audit_run_id: str, check: dict, source_id, metadata: dict, dry_run: bool = False):
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
        "created_by": "SYSTEM",
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would insert SQL check audit: {audit['title']} ({audit['severity']})")
        return

    supabase.table("system_audits").insert(audit).execute()


def categorize_audit_type(check_id: str) -> str:
    if check_id.startswith("orphan") or check_id.startswith("executed"):
        return "DB_ANOMALY"
    elif (
        check_id.startswith("invalid")
        or check_id.startswith("stale")
        or check_id.startswith("empty")
        or check_id.startswith("duplicate")
    ):
        return "DATA_QUALITY"
    else:
        return "CODE_ERROR"


def _score_log_anomalies(log_blob: str) -> int:
    """Computes an anomaly score for a log blob based on error indicators."""
    if not log_blob:
        return 0
    score = 0
    score += log_blob.count("Traceback (most recent call last)") * 10
    score += log_blob.count("CRITICAL:") * 8
    score += log_blob.count("ERROR:") * 5
    score += log_blob.count("SEMANTIC FRAGILITY ALERT") * 6
    score += log_blob.count("429 Too Many Requests") * 4
    score += log_blob.count("Internal Server Error") * 4
    score += log_blob.count("WARNING:") * 1
    return score


def select_sampled_runs(logs: list[dict], sample_size: int = 3) -> list[dict]:
    """Selects sampled runs for audit: anchor (latest run) plus anomaly-prioritized or random runs.

    Args:
        logs: List of log records ordered chronologically descending (newest first).
        sample_size: Total number of runs to sample (default: 3).

    Returns:
        List of selected log records (length <= sample_size).
    """
    if not logs or len(logs) <= sample_size:
        return list(logs)

    anchor = logs[0]
    candidates = logs[1:]

    scored_candidates = []
    for run in candidates:
        score = _score_log_anomalies(run.get("log_blob", ""))
        scored_candidates.append((score, run))

    scored_candidates.sort(key=lambda item: item[0], reverse=True)

    needed = sample_size - 1
    selected_candidates = []

    for score, run in scored_candidates:
        if score > 0 and len(selected_candidates) < needed:
            selected_candidates.append(run)

    if len(selected_candidates) < needed:
        remaining = [run for _, run in scored_candidates if run not in selected_candidates]
        num_to_pick = needed - len(selected_candidates)
        picked = random.sample(remaining, min(num_to_pick, len(remaining)))
        selected_candidates.extend(picked)

    return [anchor] + selected_candidates


def extract_log_summary(log_blob: str, max_chars: int = 15000) -> str:
    """Extracts a compact, high-signal summary of a log blob, preserving tracebacks and stage metrics.

    If log_blob is already <= max_chars, it is returned as-is.
    Otherwise, extracts key lines and traceback blocks while filtering out repetitive debug lines.
    """
    if not log_blob or len(log_blob) <= max_chars:
        return log_blob

    lines = log_blob.splitlines()
    high_signal_lines = []

    key_markers = (
        "Traceback (most recent call last)",
        "ERROR",
        "CRITICAL",
        "WARNING",
        "SEMANTIC FRAGILITY",
        "Successfully ingested",
        "No messages were",
        "Consensus reached",
        "Background consensus",
        "Promoted",
        "Starting Parallel LLM Analysis",
        "Analysis complete",
        "Executing",
        "Processing complete",
        "Market feeling",
        "Isolated LIN",
        "REJECTED",
        "Validation Passed",
        "Exception",
    )

    in_traceback = False
    traceback_lines = []

    for line in lines:
        if "Traceback (most recent call last)" in line:
            in_traceback = True
            traceback_lines = [line]
            continue

        if in_traceback:
            traceback_lines.append(line)
            if not line.startswith(" ") and not line.startswith("\t") and ":" in line:
                in_traceback = False
                high_signal_lines.extend(traceback_lines)
                traceback_lines = []
            continue

        if any(marker in line for marker in key_markers):
            high_signal_lines.append(line)

    if in_traceback and traceback_lines:
        high_signal_lines.extend(traceback_lines)

    extracted = "\n".join(high_signal_lines)

    if len(extracted) > max_chars:
        half = max_chars // 2 - 50
        return extracted[:half] + "\n\n... [TRUNCATED] ...\n\n" + extracted[-half:]

    if len(extracted) < 500 and len(log_blob) > max_chars:
        half = max_chars // 2 - 50
        return log_blob[:half] + "\n\n... [TRUNCATED] ...\n\n" + log_blob[-half:]

    return extracted


def _write_step_summary(selected_runs: list[dict], findings: list[dict]) -> None:
    """Writes an audit summary table to GITHUB_STEP_SUMMARY when available in CI."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    try:
        lines = [
            "## Weekly Ingestion & Consensus Audit",
            "",
            f"**Sampled Runs ({len(selected_runs)}):**",
        ]
        for i, run in enumerate(selected_runs):
            role = "Anchor (Latest)" if i == 0 else "Sample"
            lines.append(f"- **{role}**: `{run.get('run_id')}` ({run.get('run_date')})")
        lines.append("")

        if not findings:
            lines.append("No issues or anomalies detected across sampled runs.")
        else:
            lines.append("| Severity | Title | Run ID | Suggested Fix |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for f in findings:
                severity = f.get("severity", "MEDIUM")
                title = f.get("title", "Log finding")
                run_id = f.get("run_id", "N/A")
                suggestion = f.get("suggestion", "")
                lines.append(f"| **{severity}** | {title} | `{run_id}` | {suggestion} |")
        lines.append("")

        with open(summary_path, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write to GITHUB_STEP_SUMMARY: {e}")


async def analyze_recent_logs(supabase, audit_run_id: str, dry_run: bool = False):
    cutoff = datetime.now(UTC) - timedelta(days=7)
    cutoff_str = cutoff.isoformat()

    result = (
        supabase.table("ingestion_logs")
        .select("*")
        .gte("created_at", cutoff_str)
        .order("created_at", desc=True)
        .execute()
    )

    if not result.data:
        logger.info("No recent ingestion logs found for analysis")
        return 0

    selected_runs = select_sampled_runs(result.data, sample_size=3)
    logger.info(
        f"Selected {len(selected_runs)} runs for audit out of {len(result.data)} total runs "
        f"from past 7 days: {[r.get('run_id') for r in selected_runs]}"
    )

    summarized_blobs = []
    for r in selected_runs:
        summary_text = extract_log_summary(r.get("log_blob", ""))
        summarized_blobs.append(f"=== Run: {r.get('run_id')} ({r.get('run_date')}) ===\n{summary_text}")

    logs_combined = "\n\n".join(summarized_blobs)

    suggestions = await analyze_log_blob(logs_combined)

    if suggestions:
        findings = []
        try:
            parsed = json.loads(suggestions)
            if isinstance(parsed, list):
                findings = parsed
            else:
                findings = [{"title": "Log Finding", "severity": "MEDIUM", "suggestion": str(parsed)}]
        except Exception:
            findings = [{"title": "Log Analysis Finding", "severity": "MEDIUM", "suggestion": suggestions[:500]}]

        insert_log_audit(
            supabase,
            audit_run_id=audit_run_id,
            description=(
                f"Audited {len(selected_runs)} sampled runs ({[r.get('run_id') for r in selected_runs]}) "
                f"out of {len(result.data)} total runs from past 7 days"
            ),
            suggestions=suggestions,
            dry_run=dry_run,
        )

        _write_step_summary(selected_runs, findings)
        return len(findings)

    return 0


def insert_log_audit(supabase, audit_run_id: str, description: str, suggestions: str, dry_run: bool = False):
    audit = {
        "audit_type": "SYSTEM_LOG",
        "severity": "MEDIUM",
        "title": "System Log Analysis",
        "description": description,
        "suggestion": suggestions,
        "status": "OPEN",
        "audit_run_id": audit_run_id,
        "analysis_method": "LLM_ANALYSIS",
        "created_by": "SYSTEM",
    }

    if dry_run:
        logger.info(f"[DRY RUN] Would insert log audit: {audit['title']} ({description})")
        return

    supabase.table("system_audits").insert(audit).execute()
