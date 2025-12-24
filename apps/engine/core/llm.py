
import instructor
from openai import OpenAI, AsyncOpenAI
from anthropic import AsyncAnthropic
import google.generativeai as genai
import os
import logging
from .models import DecisionObject
from . import config

logger = logging.getLogger("engine")

# --- Client Factories ---

def get_openai_client():
    return instructor.from_openai(AsyncOpenAI(api_key=config.OPENAI_API_KEY))

def get_anthropic_client():
    return instructor.from_anthropic(AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY))

def get_deepseek_client():
    # DeepSeek uses the OpenAI SDK as its official Python client
    # Ref: https://api-docs.deepseek.com/
    return instructor.from_openai(
        AsyncOpenAI(
            api_key=config.DEEPSEEK_API_KEY, 
            base_url="https://api.deepseek.com"
        ),
        mode=instructor.Mode.JSON
    )

def get_gemini_client(model_name: str = config.GEMINI_MODEL):
    # Using the official Google Generative AI SDK
    # Ref: https://ai.google.dev/gemini-api/docs/structured-output?lang=python
    genai.configure(api_key=config.GEMINI_API_KEY)
    return instructor.from_gemini(
        genai.GenerativeModel(model_name),
        mode=instructor.Mode.GEMINI_JSON,
    )

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
        client = get_gemini_client(model_name)
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
        # Note: instructor.from_gemini returns a client that works slightly differently or 
        # wraps the call. For Gemini, it's often a synchronous-looking call or handled by the wrapper.
        # However, for consistency in our async pipeline, we check if we need to await.
        
        if provider == "gemini":
            # instructor.from_gemini currently uses the synchronous SDK wrapper mostly, 
            # but it supports response_model.
            resp = client.chat.completions.create(
                messages=[
                    {"role": "user", "content": prompt}
                ],
                response_model=DecisionObject,
            )
        else:
            resp = await client.chat.completions.create(
                model=model_name,
                response_model=DecisionObject,
                messages=[
                    {"role": "system", "content": "You are a hedge fund trading algorithm. Analyze news strictly."},
                    {"role": "user", "content": prompt}
                ],
                max_retries=2
            )
            
        resp.source_id = source_id 
        return resp

    except Exception as e:
        logger.error(f"Error analyzing with {provider}/{model_name}: {e}")
        raise e
