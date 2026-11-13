"""SQLite storage for proxy call audits, latency tracking, and provider metrics."""

import json
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class AuditDB:
    def __init__(self, db_path: str = "data/free_llm_proxy.db"):
        self.db_path = db_path
        self._persistent_conn = None
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            self._persistent_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._persistent_conn.row_factory = sqlite3.Row
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        if self._persistent_conn is not None:
            return self._persistent_conn
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS call_logs (
                id TEXT PRIMARY KEY,
                timestamp TEXT NOT NULL,
                requested_model TEXT NOT NULL,
                routed_provider TEXT NOT NULL,
                routed_model TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                latency_ms REAL NOT NULL,
                status_code INTEGER NOT NULL,
                failover_chain TEXT,
                error_message TEXT,
                client_ip TEXT,
                user_agent TEXT,
                purpose TEXT,
                prompt_preview TEXT
            )
            """
        )
        conn.commit()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(call_logs)")
        existing_cols = {
            row["name"] if isinstance(row, sqlite3.Row) else row[1]
            for row in cursor.fetchall()
        }
        for col in ["client_ip", "user_agent", "purpose", "prompt_preview"]:
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE call_logs ADD COLUMN {col} TEXT")
        migrations = {
            "is_stream": "INTEGER DEFAULT 0",
            "usage_available": "INTEGER DEFAULT 0",
            "ttft_ms": "REAL DEFAULT 0",
            "duration_ms": "REAL DEFAULT 0",
            "stream_completed": "INTEGER DEFAULT 0",
        }
        added = set()
        for col, ddl in migrations.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE call_logs ADD COLUMN {col} {ddl}")
                added.add(col)
        if "usage_available" in added:
            conn.execute(
                "UPDATE call_logs SET usage_available = "
                "CASE WHEN total_tokens > 0 THEN 1 ELSE 0 END"
            )
        if "duration_ms" in added:
            conn.execute("UPDATE call_logs SET duration_ms = latency_ms")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_call_logs_timestamp ON call_logs(timestamp)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_call_logs_status ON call_logs(status_code)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_call_logs_client_ip ON call_logs(client_ip)"
        )
        conn.commit()
        if self._persistent_conn is None:
            conn.close()

    def log_call(
        self,
        requested_model: str,
        routed_provider: str,
        routed_model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        latency_ms: float = 0.0,
        status_code: int = 200,
        failover_chain: list[str] | None = None,
        error_message: str | None = None,
        client_ip: str | None = None,
        user_agent: str | None = None,
        purpose: str | None = None,
        prompt_preview: str | None = None,
        is_stream: bool = False,
        usage_available: bool = False,
        ttft_ms: float = 0.0,
        duration_ms: float | None = None,
        stream_completed: bool = False,
    ) -> str:
        call_id = f"call_{uuid.uuid4().hex[:12]}"
        now_iso = datetime.now(UTC).isoformat()
        chain_json = json.dumps(failover_chain or [])
        duration_ms = latency_ms if duration_ms is None else duration_ms

        conn = self._get_connection()
        conn.execute(
            """
            INSERT INTO call_logs (
                id, timestamp, requested_model, routed_provider, routed_model,
                prompt_tokens, completion_tokens, total_tokens, latency_ms,
                status_code, failover_chain, error_message,
                client_ip, user_agent, purpose, prompt_preview,
                is_stream, usage_available, ttft_ms, duration_ms, stream_completed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                call_id,
                now_iso,
                requested_model,
                routed_provider,
                routed_model,
                prompt_tokens,
                completion_tokens,
                total_tokens,
                latency_ms,
                status_code,
                chain_json,
                error_message,
                client_ip,
                user_agent,
                purpose,
                prompt_preview,
                int(is_stream),
                int(usage_available),
                ttft_ms,
                duration_ms,
                int(stream_completed),
            ),
        )
        conn.commit()
        if self._persistent_conn is None:
            conn.close()
        return call_id

    def get_metrics(self) -> dict[str, Any]:
        conn = self._get_connection()
        total_reqs = conn.execute("SELECT COUNT(*) FROM call_logs").fetchone()[0]
        success_reqs = conn.execute(
            "SELECT COUNT(*) FROM call_logs WHERE status_code = 200"
        ).fetchone()[0]
        unauthorized_reqs = conn.execute(
            "SELECT COUNT(*) FROM call_logs WHERE status_code = 401"
        ).fetchone()[0]
        tokens_row = conn.execute(
            "SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens) FROM call_logs WHERE status_code = 200"
        ).fetchone()
        avg_lat = (
            conn.execute(
                "SELECT AVG(latency_ms) FROM call_logs WHERE status_code = 200"
            ).fetchone()[0]
            or 0.0
        )
        streaming_reqs = conn.execute(
            "SELECT COUNT(*) FROM call_logs WHERE status_code = 200 AND is_stream = 1"
        ).fetchone()[0]
        usage_available_reqs = conn.execute(
            "SELECT COUNT(*) FROM call_logs WHERE status_code = 200 AND usage_available = 1"
        ).fetchone()[0]
        zero_token_successes = conn.execute(
            "SELECT COUNT(*) FROM call_logs WHERE status_code = 200 AND total_tokens = 0"
        ).fetchone()[0]
        incomplete_streams = conn.execute(
            "SELECT COUNT(*) FROM call_logs "
            "WHERE status_code = 200 AND is_stream = 1 AND stream_completed = 0"
        ).fetchone()[0]
        avg_stream_duration = (
            conn.execute(
                "SELECT AVG(duration_ms) FROM call_logs "
                "WHERE status_code = 200 AND is_stream = 1 AND stream_completed = 1"
            ).fetchone()[0]
            or 0.0
        )
        avg_ttft = (
            conn.execute(
                "SELECT AVG(ttft_ms) FROM call_logs "
                "WHERE status_code = 200 AND is_stream = 1 AND ttft_ms > 0"
            ).fetchone()[0]
            or 0.0
        )

        cursor = conn.execute(
            """
            SELECT routed_provider, COUNT(*) as req_count, SUM(total_tokens) as tokens, AVG(latency_ms) as avg_lat
            FROM call_logs
            WHERE routed_provider != 'none'
            GROUP BY routed_provider
            """
        )
        providers_stats = {}
        for row in cursor.fetchall():
            providers_stats[row["routed_provider"]] = {
                "requests": row["req_count"],
                "tokens": row["tokens"] or 0,
                "avg_latency_ms": round(row["avg_lat"] or 0.0, 1),
            }

        recent_rows = conn.execute(
            """
            SELECT id, timestamp, requested_model, routed_provider, routed_model,
                   prompt_tokens, completion_tokens, total_tokens, latency_ms,
                   status_code, failover_chain, client_ip, user_agent, purpose,
                   prompt_preview, is_stream, usage_available, ttft_ms, duration_ms,
                   stream_completed
            FROM call_logs
            ORDER BY timestamp DESC
            LIMIT 10
            """
        ).fetchall()
        recent_logs = [dict(r) for r in recent_rows]

        if self._persistent_conn is None:
            conn.close()

        return {
            "total_requests": total_reqs,
            "successful_requests": success_reqs,
            "unauthorized_requests": unauthorized_reqs,
            "success_rate_pct": round(
                (success_reqs / total_reqs * 100) if total_reqs > 0 else 100.0, 1
            ),
            "streaming_requests": streaming_reqs,
            "usage_available_requests": usage_available_reqs,
            "zero_token_successes": zero_token_successes,
            "incomplete_streams": incomplete_streams,
            "token_coverage_pct": round(
                (usage_available_reqs / success_reqs * 100) if success_reqs else 0.0,
                1,
            ),
            "total_prompt_tokens": tokens_row[0] or 0,
            "total_completion_tokens": tokens_row[1] or 0,
            "total_tokens": tokens_row[2] or 0,
            "avg_latency_ms": round(avg_lat, 1),
            "avg_stream_duration_ms": round(avg_stream_duration, 1),
            "avg_ttft_ms": round(avg_ttft, 1),
            "providers": providers_stats,
            "recent_calls": recent_logs,
        }
