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
from apps.free_llm_proxy.router import Router, estimate_prompt_tokens
from apps.free_llm_proxy.security import UnauthorizedMonitor
from apps.free_llm_proxy.session import SESSION_HEADER, derive_session_id
from apps.free_llm_proxy.streaming import audited_sse_stream

app = FastAPI(title="Free LLM Proxy", version="1.0.0")

# Shared state singletons
audit_db = AuditDB(db_path=config.DB_PATH)
circuit_breaker = CircuitBreaker(default_cooldown_seconds=config.DEFAULT_COOLDOWN)
discovery = ModelDiscovery()
router = Router(circuit_breaker=circuit_breaker, discovery=discovery)
unauthorized_monitor = UnauthorizedMonitor(
    threshold=config.SECURITY_ALERT_401_THRESHOLD,
    window_seconds=config.SECURITY_ALERT_WINDOW_SECONDS,
    connector_id=config.CONNECTOR_ID,
)


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


def extract_client_info(request: Request | None) -> tuple[str, str]:
    """Extracts client IP and User-Agent from Request."""
    if not request:
        return ("unknown", "unknown")
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    user_agent = request.headers.get("user-agent", "unknown")
    return (client_ip, user_agent)


def _record_unauthorized(request: Request | None, message: str) -> None:
    """Persist a 401 attempt and feed the log-only spike monitor."""
    client_ip, user_agent = extract_client_info(request)
    audit_db.log_call(
        requested_model="unauthorized",
        routed_provider="none",
        routed_model="none",
        status_code=401,
        error_message=message,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    unauthorized_monitor.record(client_ip)


def verify_master_key(
    authorization: str | None = Header(None),
    request: Request | None = None,
) -> None:
    """Strictly validates Master API Key Bearer token and records 401 attempts."""
    expected_key = config.MASTER_KEY
    if not authorization or not authorization.startswith("Bearer "):
        _record_unauthorized(
            request,
            "Invalid or missing master API key in Authorization header.",
        )
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
        _record_unauthorized(
            request,
            "Unauthorized: Master API key does not match.",
        )
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
        "connector_id": config.CONNECTOR_ID,
        "active_providers": list(active.keys()),
        "providers_health": cb_statuses,
        "default_port": config.PORT,
    }


@app.get("/v1/models")
async def list_models(
    request: Request,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    verify_master_key(authorization, request=request)
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
async def get_metrics(
    request: Request,
    authorization: str | None = Header(None),
) -> dict[str, Any]:
    verify_master_key(authorization, request=request)
    db_metrics = audit_db.get_metrics()
    db_metrics["connector_id"] = config.CONNECTOR_ID
    db_metrics["scope"] = "connector"
    db_metrics["unauthorized_last_5m"] = unauthorized_monitor.count()
    db_metrics["unauthorized_window_seconds"] = unauthorized_monitor.window_seconds
    db_metrics["security_alert_active"] = unauthorized_monitor.alert_active
    db_metrics["circuit_breaker"] = circuit_breaker.get_status_overview()
    return db_metrics


@app.post("/v1/chat/completions")
async def chat_completions(
    request: Request,
    authorization: str | None = Header(None),
) -> Response:
    verify_master_key(authorization, request=request)
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

    # Estimate prompt size so providers with a context ceiling below it are
    # excluded from the chain before dispatch (e.g. groq's 413 at >8k tokens).
    prompt_tokens = estimate_prompt_tokens(req.messages)
    candidate_chain = router.get_candidate_chain(req.model, prompt_tokens=prompt_tokens)
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

        # Fail closed on money: never dispatch a paid request against an unknown catalog.
        if p_cfg.get("billing") == "paid" and not available_models:
            failover_log.append(f"{p_id} (catalog unavailable; paid dispatch refused)")
            last_error = {
                "error": {
                    "message": f"{p_id} catalog discovery failed; refusing paid dispatch",
                    "type": "provider_unavailable",
                }
            }
            continue

        # OpenCode Go requires a stable session header for routing and prompt caching
        dispatch_cfg = p_cfg
        if p_id == "opencode-go":
            session_id = derive_session_id(
                raw_body.get("messages") or [],
                client_ip=client_ip,
                user_agent=user_agent,
                provided=request.headers.get(SESSION_HEADER),
            )
            dispatch_cfg = {
                **p_cfg,
                "extra_headers": {
                    **p_cfg.get("extra_headers", {}),
                    SESSION_HEADER: session_id,
                },
            }
        target_model = router.resolve_model_for_provider(
            p_id, req.model, available_models
        )
        if p_id == "openrouter" and not (
            target_model.endswith(":free") or target_model == "openrouter/free"
        ):
            target_model = "openrouter/free"

        # Build payload copy with resolved target model
        payload = dict(raw_body)
        payload["model"] = target_model

        # Cloud free-tier providers enforce an output token limit; clamp when routing to cloud
        if p_id != "strata":
            # Strip Strata-specific kwargs that cloud gateways (Gemini, OVHCloud) reject with 400
            payload.pop("reasoning_budget_tokens", None)
            if "max_tokens" in payload and payload["max_tokens"] is not None:
                if payload["max_tokens"] > config.CLOUD_MAX_OUTPUT_TOKENS:
                    payload["max_tokens"] = config.CLOUD_MAX_OUTPUT_TOKENS
            if (
                "max_completion_tokens" in payload
                and payload["max_completion_tokens"] is not None
            ):
                if payload["max_completion_tokens"] > config.CLOUD_MAX_OUTPUT_TOKENS:
                    payload["max_completion_tokens"] = config.CLOUD_MAX_OUTPUT_TOKENS

        status_code, body_or_gen, resp_headers = await execute_completion(
            provider_cfg=dispatch_cfg,
            payload=payload,
            stream=req.stream,
        )

        # In-provider cascade for Gemini when high demand (503) or rate-limit (429) occurs
        if p_id == "gemini" and status_code in (429, 503):
            gemini_fallbacks = [
                m
                for m in [
                    "gemini-flash-latest",
                    "gemini-3.8-flash",
                    "gemini-3.6-flash",
                    "gemini-3.5-flash",
                ]
                if m != target_model and not target_model.endswith(m)
            ]
            for fallback_model in gemini_fallbacks:
                payload["model"] = fallback_model
                status_code, body_or_gen, resp_headers = await execute_completion(
                    provider_cfg=dispatch_cfg,
                    payload=payload,
                    stream=req.stream,
                )
                if status_code == 200:
                    target_model = fallback_model
                    break

        # In-provider cascade for OpenRouter when high demand (503) or rate-limit (429) occurs
        if p_id == "openrouter" and status_code in (429, 503):
            or_fallbacks = [
                m
                for m in [
                    "openrouter/free",
                    "nvidia/nemotron-3-ultra-550b-a55b:free",
                    "nvidia/nemotron-3.5-super-vl:free",
                    "nvidia/nemotron-3.5-lightning:free",
                ]
                if m != target_model and not target_model.endswith(m)
            ]
            for fallback_model in or_fallbacks:
                payload["model"] = fallback_model
                status_code, body_or_gen, resp_headers = await execute_completion(
                    provider_cfg=dispatch_cfg,
                    payload=payload,
                    stream=req.stream,
                )
                if status_code == 200:
                    target_model = fallback_model
                    break

        # In-provider cascade for NVIDIA NIM when deprecated function (404) or rate-limit occurs
        if p_id == "nvidia" and status_code in (404, 429, 503):
            nvidia_fallbacks = [
                m
                for m in [
                    "minimaxai/minimax-m3.1-flash",
                    "nvidia/nemotron-3.5-super-vl-120b-a12b",
                    "nvidia/nemotron-3-ultra-550b-a55b",
                    "mistralai/mistral-large-4-1t-a52b",
                ]
                if m != target_model and not target_model.endswith(m)
            ]
            for fallback_model in nvidia_fallbacks:
                payload["model"] = fallback_model
                status_code, body_or_gen, resp_headers = await execute_completion(
                    provider_cfg=dispatch_cfg,
                    payload=payload,
                    stream=req.stream,
                )
                if status_code == 200:
                    target_model = fallback_model
                    break

        # In-provider cascade for Kilo Code when paid model (401) or rate-limit occurs
        if p_id == "kilo" and status_code in (400, 401, 429, 503):
            kilo_fallbacks = [
                m
                for m in [
                    "kilo-auto/free",
                    "reflection/beam-free",
                    "nvidia/nemotron-3.5-super-vl:free",
                ]
                if m != target_model and not target_model.endswith(m)
            ]
            for fallback_model in kilo_fallbacks:
                payload["model"] = fallback_model
                status_code, body_or_gen, resp_headers = await execute_completion(
                    provider_cfg=dispatch_cfg,
                    payload=payload,
                    stream=req.stream,
                )
                if status_code == 200:
                    target_model = fallback_model
                    break

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

        if status_code == 200:
            circuit_breaker.record_success(p_id)

            if req.stream:

                def _log_stream(result: dict[str, Any]) -> None:
                    usage = result.get("usage") or {}
                    audit_db.log_call(
                        requested_model=req.model,
                        routed_provider=p_id,
                        routed_model=target_model,
                        prompt_tokens=int(usage.get("prompt_tokens", 0) or 0),
                        completion_tokens=int(usage.get("completion_tokens", 0) or 0),
                        total_tokens=int(usage.get("total_tokens", 0) or 0),
                        latency_ms=elapsed_ms,
                        status_code=200,
                        failover_chain=failover_log,
                        error_message=result.get("error"),
                        client_ip=client_ip,
                        user_agent=user_agent,
                        purpose=purpose,
                        prompt_preview=prompt_preview,
                        is_stream=True,
                        usage_available=result.get("usage") is not None,
                        ttft_ms=float(result.get("ttft_ms") or 0.0),
                        duration_ms=float(result.get("duration_ms") or elapsed_ms),
                        stream_completed=bool(result.get("completed")),
                    )

                return StreamingResponse(
                    audited_sse_stream(
                        body_or_gen,
                        _log_stream,
                        started_at=start_time,
                    ),
                    media_type="text/event-stream",
                )

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
                    usage_available=bool(usage),
                    duration_ms=elapsed_ms,
                    stream_completed=True,
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
                "message": "All provider candidates failed or rate-limited.",
                "failover_chain": failover_log,
                "last_error": last_error,
            }
        },
    )
