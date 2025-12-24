
import instructor
from openai import OpenAI, AsyncOpenAI
from anthropic import AsyncAnthropic
from google import genai
import os
import logging
from .models import DecisionObject
from . import config

logger = logging.getLogger("engine")

# --- Client Factories ---

def get_openai_client():
    return instructor.from_openai(AsyncOpenAI(
        api_key=config.OPENAI_API_KEY,
        timeout=60.0 # 60s timeout
    ))

def get_anthropic_client():
    return instructor.from_anthropic(AsyncAnthropic(
        api_key=config.ANTHROPIC_API_KEY,
        timeout=60.0
    ))

def get_deepseek_client():
    # DeepSeek uses the OpenAI SDK as its official Python client
    return instructor.from_openai(
        AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com",
            timeout=60.0
        ),
        mode=instructor.Mode.JSON
    )

def get_gemini_client():
    # Using the new official Google Gen AI SDK
    client = genai.Client(api_key=config.GEMINI_API_KEY)
    return instructor.from_genai(client)

# --- Analysis Functions ---

async def analyze_with_provider(provider: str, model_name: str, text: str, source_id: str) -> DecisionObject:
    """
    Analyzes text using the specified provider and returns a DecisionObject.
    """
    client = None
    if provider == "openai":
        client = get_openai_client()
    elif provider == "anthropic":
        client = get_anthropic_client()
    elif provider == "deepseek":
        client = get_deepseek_client()
    elif provider == "gemini":
        client = get_gemini_client()
    else:
        raise ValueError(f"Unknown provider: {provider}")

    prompt = f"""
    Analyze the following financial news snippet and determine a trading signal (BUY, SELL, HOLD) for the relevant ticker.
    You must provide a confidence score (0-100) and your reasoning.
    
    News Snippet:
    "{text}"
    
    Return the result as a structured JSON object matching the schema.
    """

    try:
        # Note: instructor handles common interface for create()
        
        args = {
            "model": model_name,
            "response_model": DecisionObject,
            "messages": [
                {"role": "system", "content": "You are a hedge fund trading algorithm. Analyze news strictly."},
                {"role": "user", "content": prompt}
            ],
            "max_retries": 2
        }

        # For Gemini, the new genai SDK wrapper with instructor supports await for chat.completions.create
        resp_awaitable = client.chat.completions.create(**args)
        
        if hasattr(resp_awaitable, "__await__") or asyncio.iscoroutine(resp_awaitable):
            resp = await resp_awaitable
        else:
            resp = resp_awaitable
            
        resp.source_id = source_id 
        return resp

    except Exception as e:
        logger.error(f"Error analyzing with {provider}/{model_name}: {e}")
        raise e
