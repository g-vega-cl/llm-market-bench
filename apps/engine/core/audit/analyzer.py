import json
import logging
from openai import AsyncOpenAI
from core.config import DEEPSEEK_MODEL

logger = logging.getLogger("engine")

DEEPSEEK_API_KEY = None

def configure(api_key: str):
    global DEEPSEEK_API_KEY
    DEEPSEEK_API_KEY = api_key


async def analyze_log_blob(log_blob: str) -> str:
    if not DEEPSEEK_API_KEY:
        logger.error("DeepSeek API key not configured")
        return None

    truncated_blob = log_blob[-32000:] if len(log_blob) > 32000 else log_blob

    prompt = f"""Analyze the following ingestion log blob. Identify any errors, failures, warnings, or anomalies. 
For each issue found, provide:
1. A brief title describing the issue
2. Severity (LOW, MEDIUM, HIGH, or CRITICAL)
3. A suggested fix

Log blob:
{truncated_blob}

Return a JSON array of findings with keys: title, severity, suggestion. Return only the JSON array, no other text."""

    try:
        client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com"
        )

        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1
        )

        content = response.choices[0].message.content.strip()

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
    except Exception as e:
        logger.error(f"Log analysis failed: {e}")
        return None