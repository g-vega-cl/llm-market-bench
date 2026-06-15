import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pydantic import BaseModel

from core.config import logger
from core.db import get_supabase_client
from core.llm.clients import close_client, get_gemini_client


class MetaPromptResponse(BaseModel):
    new_prompt: str


def calculate_baseline_score(predictions: list[dict]) -> float:
    """Calculate the baseline score from a set of model predictions."""
    if not predictions:
        return 0.0

    best_score = 0.0
    for p in predictions:
        s_score = p.get("sector_percentile_score") or 0.0
        p_score = p.get("pair_percentile_score") or 0.0

        avg_score = (s_score + p_score) / 2.0
        if avg_score > best_score:
            best_score = avg_score

    return float(best_score)


async def generate_new_prompt(old_prompt: str, baseline_score: float, meta_researcher) -> str:
    """Generate a new prompt variant."""

    meta_prompt = (
        "You are a Meta-Researcher AI tasked with improving an LLM's system prompt "
        "for predicting the best performing market sectors and uncorrelated pairs.\n\n"
        f"The current prompt achieved a percentile score of {baseline_score:.1f}/100.0.\n"
        "Your goal is to rewrite the prompt to be more effective, focusing on deeper logic "
        "and better data extraction. Keep the REQUIRED OUTPUT FORMAT exactly the same.\n\n"
        "CURRENT PROMPT:\n"
        f"```text\n{old_prompt}\n```\n\n"
        "Output ONLY the new raw prompt text."
    )

    try:
        resp = await meta_researcher.chat.completions.create(
            model="gemini-3.1-flash-lite",
            response_model=MetaPromptResponse,
            messages=[{"role": "user", "content": meta_prompt}],
        )
        new_prompt = resp.new_prompt
        # Clean up any markdown blocks if the LLM wrapped the output
        if new_prompt.startswith("```"):
            lines = new_prompt.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            new_prompt = "\n".join(lines).strip()
        return new_prompt
    except Exception as e:
        logger.error(f"Error generating new prompt: {e}")
        return old_prompt


async def run_predictor_autoresearch():
    client = get_supabase_client()

    # 1. Fetch evaluated predictions from the last week
    # Assuming run weekly, we fetch where status = 'evaluated' and prediction_date is recent
    # For simplicity, just fetching the latest evaluated predictions
    response = (
        client.table("sector_predictions")
        .select("*")
        .eq("status", "evaluated")
        .order("target_date", desc=True)
        .limit(10)
        .execute()
    )

    predictions = response.data
    if not predictions:
        logger.info("No evaluated predictions found. Skipping autoresearch.")
        return

    baseline_score = calculate_baseline_score(predictions)

    # 2. Fetch current active prompt
    prompt_response = (
        client.table("prompt_experiments")
        .select("*")
        .eq("prompt_name", "SECTOR_PREDICTOR_PROMPT")
        .eq("status", "active")
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not prompt_response.data:
        logger.warning("No active SECTOR_PREDICTOR_PROMPT found. Cannot run autoresearch.")
        return

    current_prompt = prompt_response.data[0]["prompt_content"]
    parent_tag = prompt_response.data[0]["variant_tag"]

    # 3. Generate new prompt
    meta_researcher = get_gemini_client()
    try:
        new_prompt = await generate_new_prompt(current_prompt, baseline_score, meta_researcher)
    finally:
        await close_client(meta_researcher, "gemini")

    if new_prompt == current_prompt:
        logger.info("New prompt is identical to old prompt. Skipping insertion.")
        return

    # 4. Insert new prompt and mark old as kept
    new_tag = f"sector-pred-{uuid.uuid4().hex[:8]}"
    today = datetime.now(UTC).date()
    week_end = today + timedelta(days=7)

    # Mark old as kept or discarded based on logic (simplified here)
    client.table("prompt_experiments").update({"status": "kept"}).eq("variant_tag", parent_tag).execute()

    client.table("prompt_experiments").insert(
        {
            "variant_tag": new_tag,
            "prompt_name": "SECTOR_PREDICTOR_PROMPT",
            "prompt_content": new_prompt,
            "week_start": today.isoformat(),
            "week_end": week_end.isoformat(),
            "status": "active",
            "experiment_type": "incremental",
            "parent_tag": parent_tag,
            "change_description": f"Autoresearch generated from baseline {baseline_score:.1f}",
        }
    ).execute()

    logger.info(f"Successfully generated and deployed new predictor prompt: {new_tag}")


if __name__ == "__main__":
    asyncio.run(run_predictor_autoresearch())
