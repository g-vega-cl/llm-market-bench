"""Policy Lookup utility for disambiguating vague government policy references.

When a newsletter chunk mentions government policy without naming a specific
bill, act, or regulation, this utility uses Gemini with Google Search to identify
the specific policy and its current status.
"""

import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from core import config

logger = logging.getLogger("engine")


class PolicyLookupResult(BaseModel):
    """Result of a policy lookup operation."""

    policy_name: str = Field(..., description="Specific name of the bill, act, or regulation")
    status: str = Field(..., description="Current status (e.g., 'in committee', 'passed House', 'signed into law')")
    description: str = Field(..., description="1-sentence description of what the policy does and market relevance")
    confidence: int = Field(..., description="Confidence score 0-100 that this is the correct policy")


POLICY_LOOKUP_PROMPT = """Identify the specific government bill, act, policy, or regulation discussed or implied in the following text. Use web search to find the most relevant, currently active policy.

TEXT:
{chunk_content}

Return ONLY a JSON object with:
- "policy_name": The specific name of the bill, act, or regulation. Examples: "Farm, Food and National Security Act of 2026", "CHIPS and Science Act", "EU Green Hydrogen Acceleration Act". If no specific policy can be identified, use "UNKNOWN".
- "status": Current legislative/regulatory status. Examples: "signed into law", "passed House", "in committee", "proposed", "executive order issued", "stalled". If unknown, use "status unclear".
- "description": A 1-sentence description of what the policy does and its market relevance (e.g., "Provides $50B in subsidies for domestic semiconductor manufacturing, benefiting chip equipment makers").
- "confidence": Integer 0-100. 100 = exact match verified. 0 = no relevant policy found.

Do NOT include any text outside the JSON object."""


async def lookup_policy(chunk_content: str, existing_event_name: str | None = None) -> PolicyLookupResult | None:
    """Looks up a specific government policy from vague text using Gemini + Google Search.

    Args:
        chunk_content: The newsletter chunk text containing policy references.
        existing_event_name: Optional existing vague event name for additional context.

    Returns:
        PolicyLookupResult if a policy is identified with confidence >= 50, None otherwise.
    """
    context = chunk_content
    if existing_event_name:
        context = f"Existing vague event name: {existing_event_name}\n\n{context}"

    prompt = POLICY_LOOKUP_PROMPT.format(chunk_content=context)

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    try:
        response = await client.aio.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search={})],
                temperature=0.0,
                max_output_tokens=1024,
            ),
        )

        text = response.text.strip() if response.text else ""

        if not text:
            logger.warning("PolicyLookup: Empty response from Gemini.")
            return None

        json_start = text.find("{")
        json_end = text.rfind("}") + 1
        if json_start == -1 or json_end == 0:
            logger.warning(f"PolicyLookup: No JSON found in response: {text[:200]}")
            return None

        json_str = text[json_start:json_end]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning(f"PolicyLookup: Failed to parse JSON: {json_str[:200]}")
            return None

        policy_name = data.get("policy_name", "").strip()
        if not policy_name or policy_name.upper() == "UNKNOWN":
            logger.info("PolicyLookup: No specific policy identified in chunk.")
            return None

        confidence = int(data.get("confidence", 0))
        if confidence < 50:
            logger.info(f"PolicyLookup: Low confidence ({confidence}) for '{policy_name}', rejecting.")
            return None

        result = PolicyLookupResult(
            policy_name=policy_name,
            status=data.get("status", "status unclear"),
            description=data.get("description", ""),
            confidence=confidence,
        )

        logger.info(f"PolicyLookup: Identified '{policy_name}' [{result.status}] with confidence {confidence}%")
        return result

    except Exception as e:
        logger.error(f"PolicyLookup failed: {e}")
        return None
    finally:
        try:
            if hasattr(client, "_async_httpx_client") and client._async_httpx_client is not None:
                await client._async_httpx_client.aclose()
        except Exception:
            pass
