"""FastAPI Server exposing OpenAI-compatible /v1 endpoints with dynamic failover."""

import secrets
import time
from typing import Any
from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from apps.free_llm_proxy import config
from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.client import execute_completion
from apps.free_llm_proxy.db import AuditDB
from apps.free_llm_proxy.discovery import ModelDiscovery
from apps.free_llm_proxy.models import ChatCompletionRequest
from apps.free_llm_proxy.router import Router

app = FastAPI(title="Free LLM Proxy", version="1.0.0")

# Shared state singletons
audit_db = AuditDB(db_path=config.DB_PATH)
circuit_breaker = CircuitBreaker(default_cooldown_seconds=config.DEFAULT_COOLDOWN)
discovery = ModelDiscovery()
router = Router(circuit_breaker=circuit_breaker, discovery=discovery)


def extract_prompt_preview(messages: list[Any], max_length: int = 60) -> str | None:
    """Extract a concise text snippet (up to max_length chars) of caller intent/why."""
    if not messages:
        return None
    user_msgs = [m for m in messages if getattr(m, "role", "") == "user"]
    target = user_msgs[-1] if user_msgs else messages[-1]
    content = getattr(target, "content", None)
    if isinstance(content, str):
        text = " ".join(content.split()).strip()
        if not text:
            return None
        return text[:max_length] + ("..." if len(text) > max_length else "")
    elif isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                txt = part.get("text", "")
                if txt:
                    parts.append(txt)
        text = " ".join(" ".join(parts).split()).strip()
        if not text:
            return None
        return text[:max_length] + ("..." if len(text) > max_length else "")
    return None


def verify_master_key(authorization: str | None = Header(None)) -> None:
    """Strictly validates Master API Key Bearer token."""
    expected_key = config.MASTER_KEY
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Invalid or missing master API key in Authorization header.",
                    "type": "auth_error",
                }
            },
        )
    provided_key = authorization.split("Bearer ", 1)[1].strip()
    if not secrets.compare_digest(provided_key, expected_key):
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "Unauthorized: Master API key does not match.",
                    "type": "auth_error",
                }
            },
        )


@app.get("/health")
async def health_check() -> dict[str, Any]:
    active = router.get_active_providers()
    cb_statuses = circuit_breaker.get_status_overview()
    return {
        "status": "ok",
        "active_providers": list(active.keys()),
        "providers_health": cb_statuses,
        "default_port": config.PORT,
    }


@app.get("/v1/models")
async def list_models(authorization: str | None = Header(None)) -> dict[str, Any]:
    verify_master_key(authorization)
    active = router.get_active_providers()
    model_entries = []

    # Include virtual aliases
    for alias in router.virtual_aliases:
        model_entries.append(
            {
                "id": alias,
                "object": "model",
                "owned_by": "free-llm-proxy",
                "permission": [],
            }
        )

    # Include discovered models from active providers
    for p_id, p_cfg in active.items():
        base_url = p_cfg["base_url"]
        headers = {}
        if p_cfg.get("api_key"):
            headers["Authorization"] = f"Bearer {p_cfg['api_key']}"
        models = await discovery.fetch_live_models(p_id, base_url, headers)
        for m in models:
            model_entries.append(
                {
                    "id": f"{p_id}/{m}",
                    "object": "model",
                    "owned_by": p_id,
                    "permission": [],
                }
            )

    return {"object": "list", "data": model_entries}


@app.get("/v1/metrics")
@app.get("/stats")
async def get_metrics(authorization: str | None = Header(None)) -> dict[str, Any]:
    verify_master_key(authorization)
    db_metrics = audit_db.get_metrics()
    db_metrics["circuit_breaker"] = circuit_breaker.get_status_overview()
    return db_metrics


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: str | None = Header(None),
) -> Response:
    verify_master_key(authorization)
    raw_body = await request.json()
    try:
        req = ChatCompletionRequest(**raw_body)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "message": f"Invalid request payload: {e}",
                    "type": "invalid_request_error",
                }
            },
        ) from e

    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "unknown")
    purpose = (
        request.headers.get("x-purpose")
        or request.headers.get("x-client-id")
        or request.headers.get("x-caller-reason")
        or None
    )
    prompt_preview = extract_prompt_preview(req.messages, max_length=60)

    candidate_chain = router.get_candidate_chain(req.model)
    if not candidate_chain:
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "message": "No active providers available in pool. Please check .env credentials.",
                    "type": "no_providers",
                }
            },
        )

    start_time = time.perf_counter()
    failover_log = []
    last_error = None

    for p_id, p_cfg in candidate_chain:
        # Fetch or resolve target model for this candidate
        base_url = p_cfg["base_url"]
        headers = (
            {"Authorization": f"Bearer {p_cfg['api_key']}"}
            if p_cfg.get("api_key")
            else {}
        )
        available_models = await discovery.fetch_live_models(p_id, base_url, headers)
        target_model = router.resolve_model_for_provider(
            p_id, req.model, available_models
        )

        # Build payload copy with resolved target model
        payload = dict(raw_body)
        payload["model"] = target_model

        status_code, body_or_gen, resp_headers = await execute_completion(
            provider_cfg=p_cfg,
            payload=payload,
            stream=req.stream,
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

        if status_code == 200:
            circuit_breaker.record_success(p_id)

            if req.stream:
                audit_db.log_call(
                    requested_model=req.model,
                    routed_provider=p_id,
                    routed_model=target_model,
                    prompt_tokens=0,
                    completion_tokens=0,
                    total_tokens=0,
                    latency_ms=elapsed_ms,
                    status_code=200,
                    failover_chain=failover_log,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    purpose=purpose,
                    prompt_preview=prompt_preview,
                )
                return StreamingResponse(body_or_gen, media_type="text/event-stream")

            else:
                # Ensure choices have a string content even if reasoning models omitted it
                if isinstance(body_or_gen, dict):
                    for choice in body_or_gen.get("choices", []):
                        msg = choice.get("message", {})
                        if "content" not in msg or msg["content"] is None:
                            msg["content"] = ""

                usage = body_or_gen.get("usage", {})
                audit_db.log_call(
                    requested_model=req.model,
                    routed_provider=p_id,
                    routed_model=target_model,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    latency_ms=elapsed_ms,
                    status_code=200,
                    failover_chain=failover_log,
                    client_ip=client_ip,
                    user_agent=user_agent,
                    purpose=purpose,
                    prompt_preview=prompt_preview,
                )
                return JSONResponse(content=body_or_gen, status_code=200)

        else:
            # Trip circuit breaker and try next candidate
            retry_after = resp_headers.get("retry-after") or resp_headers.get(
                "ratelimit-reset"
            )
            circuit_breaker.record_failure(
                p_id, status_code=status_code, retry_after=retry_after
            )
            failover_log.append(f"{p_id} (HTTP {status_code})")
            last_error = body_or_gen

    # If all candidates in chain failed
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
    audit_db.log_call(
        requested_model=req.model,
        routed_provider="none",
        routed_model="none",
        latency_ms=elapsed_ms,
        status_code=502,
        failover_chain=failover_log,
        error_message=str(last_error),
        client_ip=client_ip,
        user_agent=user_agent,
        purpose=purpose,
        prompt_preview=prompt_preview,
    )
    return JSONResponse(
        status_code=502,
        content={
            "error": {
                "message": "All free providers failed or rate-limited.",
                "failover_chain": failover_log,
                "last_error": last_error,
            }
        },
    )
