import json
import logging

from core.config import AUTO_GO_MODEL, FREE_PROXY_MASTER_KEY
from core.llm.clients import get_auto_go_raw_client

logger = logging.getLogger("engine")

FREE_PROXY_API_KEY: str | None = None
DEEPSEEK_API_KEY: str | None = None  # Legacy alias preserved for test compatibility


def configure(api_key: str | None):
    global FREE_PROXY_API_KEY, DEEPSEEK_API_KEY
    FREE_PROXY_API_KEY = api_key
    DEEPSEEK_API_KEY = api_key


async def analyze_log_blob(log_blob: str) -> str | None:
    resolved_key = ((DEEPSEEK_API_KEY or FREE_PROXY_API_KEY or FREE_PROXY_MASTER_KEY) or "").strip()
    if not resolved_key:
        logger.error("Free proxy master key not configured")
        return None

    truncated_blob = log_blob[-32000:] if len(log_blob) > 32000 else log_blob

    prompt = f"""Analyze the following sampled ingestion and consensus logs from the weekly pipeline. Identify any errors, failures, warnings, or anomalies.
Pay special attention to:
1. Ingestion failures (email authentication/IMAP issues, empty snapshots, template/fragility alerts, calendar parsing).
2. Consensus anomalies (promoted events failing, debate or synthesis crashes, rate limits, zero promoted events).
3. Model and execution failures (provider timeouts, schema parsing errors, trade rejection anomalies).

For each issue found, provide:
- title: Brief title describing the issue
- severity: LOW, MEDIUM, HIGH, or CRITICAL
- suggestion: Actionable suggested fix or investigation step
- run_id: The specific run ID where the issue occurred (if identifiable from '=== Run: <run_id> ===')

Logs:
{truncated_blob}

Return a JSON array of findings with keys: title, severity, suggestion, run_id. Return only the JSON array, no other text."""

    client = None
    content = ""
    try:
        client = get_auto_go_raw_client(api_key=resolved_key, purpose="weekly-log-audit")

        response = await client.chat.completions.create(
            model=AUTO_GO_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0.1
        )

        choices = getattr(response, "choices", None) or []
        raw_content = getattr(choices[0].message, "content", None) if choices else None
        if not raw_content:
            logger.error("auto-go log analysis returned empty choices/content")
            return None
        content = raw_content.strip()

        if "<think>" in content and "</think>" in content:
            content = content.split("</think>", 1)[1].strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        findings = json.loads(content)
        return json.dumps(findings, indent=2)

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse LLM response as JSON: {e}")
        return f"Raw analysis:\n{content[:2000]}"
    except Exception:
        logger.exception("Log analysis failed")
        return None
    finally:
        if client is not None and hasattr(client, "close"):
            try:
                await client.close()
            except Exception as close_err:
                logger.warning("Failed to close auto-go client: %s", close_err)
