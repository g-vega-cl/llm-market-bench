"""FastAPI Server exposing OpenAI-compatible /v1 endpoints with dynamic failover."""

import asyncio
from collections.abc import Callable
import logging
import secrets
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse

from apps.free_llm_proxy import config
from apps.free_llm_proxy.circuit_breaker import CircuitBreaker
from apps.free_llm_proxy.client import execute_completion
from apps.free_llm_proxy.db import AuditDB
from apps.free_llm_proxy.discovery import ModelDiscovery, is_allowed_model
from apps.free_llm_proxy.failover import (
    MIN_ATTEMPT_SECONDS,
    UNCAPPED,
    attempt_budget,
    cascade_candidates,
    is_empty_completion,
    is_futile_rate_limit,
    is_plan_model,
    opencode_go_attempts,
    segment_remaining_s,
)
from apps.free_llm_proxy.models import ChatCompletionRequest
from apps.free_llm_proxy.request_helpers import (
    apply_output_ceiling,
    apply_thinking_params,
    extract_client_info,
    extract_prompt_preview,
    extract_purpose,
    failure_priority,
    is_explicit_paid_request,
    normalize_non_streaming_choices,
    resolve_candidate_model,
)
from apps.free_llm_proxy.router import Router, estimate_prompt_tokens
from apps.free_llm_proxy.security import UnauthorizedMonitor
from apps.free_llm_proxy.session import SESSION_HEADER, derive_session_id
from apps.free_llm_proxy.streaming import (
    audited_sse_stream,
    close_stream_source,
    prefixed_stream,
    prime_sse_stream,
)

app = FastAPI(title="Free LLM Proxy", version="1.0.0")

logger = logging.getLogger("free_llm_proxy.server")

# Shared state singletons
audit_db = AuditDB(db_path=config.DB_PATH)
circuit_breaker = CircuitBreaker(default_cooldown_seconds=config.DEFAULT_COOLDOWN)
discovery = ModelDiscovery()
router = Router(circuit_breaker=circuit_breaker, discovery=discovery)

# One-time relabel of rows written before call_logs carried a billing column.
try:
    _PAID_PROVIDERS = [
        pid
        for pid, cfg in (router.providers or {}).items()
        if cfg.get("billing") == "paid"
    ]
    audit_db.backfill_paid_billing(_PAID_PROVIDERS)
except Exception:  # pragma: no cover - startup hygiene must never block serving
    audit_db  # noqa: B018

unauthorized_monitor = UnauthorizedMonitor(
    threshold=config.SECURITY_ALERT_401_THRESHOLD,
    window_seconds=config.SECURITY_ALERT_WINDOW_SECONDS,
    connector_id=config.CONNECTOR_ID,
)


async def _dispatch_with_timeout(
    provider_id: str,
    provider_cfg: dict[str, Any],
    payload: dict[str, Any],
    stream: bool,
    budget_s: float | None = None,
) -> tuple[int, Any, dict[str, str]]:
    """Dispatch upstream completion with a wall-clock cap for non-Strata cloud routes.

    ``budget_s`` tightens the configured cap for this one attempt (the free
    segment's remaining budget, or the paid tier's own smaller cap). ``None``
    keeps the provider-wide default.
    """
    timeout = config.CLOUD_REQUEST_TIMEOUT_SECONDS
    if provider_id == "strata" or timeout <= 0:
        status_code, body_or_gen, resp_headers = await execute_completion(
            provider_cfg=provider_cfg,
            payload=payload,
            stream=stream,
        )
    else:
        if budget_s is not None:
            timeout = min(timeout, budget_s)
        try:
            status_code, body_or_gen, resp_headers = await asyncio.wait_for(
                execute_completion(
                    provider_cfg=provider_cfg,
                    payload=payload,
                    stream=stream,
                ),
                timeout=timeout,
            )
        except TimeoutError:
            return (
                504,
                {
                    "error": {
                        "message": f"Provider {provider_id} request timed out after {timeout:.1f}s.",
                        "type": "timeout_error",
                    }
                },
                {},
            )

    # Reasoning exhaustion or silent 0-token upstreams return HTTP 200 with no visible
    # output; convert to 503 so in-provider cascades and cross-provider failover recover.
    if not stream and status_code == 200 and is_empty_completion(body_or_gen):
        logger.warning(
            "Provider %s model %s returned HTTP 200 with an empty completion; failing over",
            provider_id,
            payload.get("model"),
        )
        return (
            503,
            {
                "error": {
                    "message": f"Provider {provider_id} returned an empty completion.",
                    "type": "empty_completion",
                }
            },
            resp_headers,
        )
    return status_code, body_or_gen, resp_headers


async def _dispatch_candidate_attempts(
    p_id: str,
    p_cfg: dict[str, Any],
    dispatch_cfg: dict[str, Any],
    payload: dict[str, Any],
    attempt_models: list[tuple[str, bool]],
    *,
    stream: bool,
    is_paid: bool,
    metered_used: int,
    remaining_fn: Callable[[], float],
    failover_log: list[str],
) -> tuple[tuple[int, Any, dict[str, str]], str | None, int, dict[str, Any] | None]:
    """Dispatches this candidate's models in order, spending at most one metered call.

    Returns ``((status, body, headers), answered_model, metered_used, skip_error)``.
    A skipped candidate returns status ``0`` with the reason already recorded in
    ``failover_log``, so the caller never mistakes a harness deadline for a
    provider response.
    """
    status_code: int = 0
    body_or_gen: Any = None
    resp_headers: dict[str, str] = {}
    skip_error: dict[str, Any] | None = None

    for attempt_model, metered in attempt_models:
        if metered and metered_used >= 1:
            failover_log.append(
                f"{p_id} ({attempt_model} skipped: metered attempt already spent)"
            )
            break
        budget = UNCAPPED if stream else attempt_budget(p_cfg, remaining_fn())
        if budget.skip:
            segment = "paid" if is_paid else "free"
            failover_log.append(f"{p_id} (skipped: {segment} pass deadline exhausted)")
            skip_error = {
                "error": {
                    "message": (
                        f"{p_id} skipped: the {segment} segment budget is spent; "
                        "raise FREE_PASS_DEADLINE_SECONDS / "
                        "PAID_PASS_DEADLINE_SECONDS (0 disables)"
                    ),
                    "type": "timeout_error",
                }
            }
            break
        payload["model"] = attempt_model
        status_code, body_or_gen, resp_headers = await _dispatch_with_timeout(
            provider_id=p_id,
            provider_cfg=dispatch_cfg,
            payload=payload,
            stream=stream,
            budget_s=budget.cap_s,
        )
        if metered:
            metered_used += 1
        if status_code == 200:
            return (
                (status_code, body_or_gen, resp_headers),
                attempt_model,
                metered_used,
                None,
            )

    return (status_code, body_or_gen, resp_headers), None, metered_used, skip_error


async def _cascade_in_provider(
    provider_id: str,
    provider_cfg: dict[str, Any],
    dispatch_cfg: dict[str, Any],
    payload: dict[str, Any],
    target_model: str,
    result: tuple[int, Any, dict[str, str]],
    *,
    available_models: list[str] | None = None,
    stream: bool,
    remaining_fn: Callable[[], float],
) -> tuple[int, Any, dict[str, str], str]:
    """Retries adjacent models on the same provider after a transient failure.

    Returns the winning ``(200, body, headers)`` or preserves the highest-priority
    failure status (429 > 4xx > 5xx > 404) so fallback errors never mask rate
    limits from the circuit breaker.
    """
    initial_status, initial_body, initial_headers = result
    fallbacks = cascade_candidates(
        provider_id, provider_cfg, initial_status, target_model, available_models
    )
    if not fallbacks:
        return initial_status, initial_body, initial_headers, target_model

    status_code, body_or_gen, resp_headers = result
    best_failure = result
    allowed = provider_cfg.get("allowed_model_patterns")
    for fallback_model in fallbacks:
        if allowed is not None and not is_allowed_model(fallback_model, allowed):
            continue
        if is_futile_rate_limit(status_code, body_or_gen):
            break
        budget = UNCAPPED if stream else attempt_budget(provider_cfg, remaining_fn())
        if budget.skip:
            break
        payload["model"] = fallback_model
        status_code, body_or_gen, resp_headers = await _dispatch_with_timeout(
            provider_id=provider_id,
            provider_cfg=dispatch_cfg,
            payload=payload,
            stream=stream,
            budget_s=budget.cap_s,
        )
        if status_code == 200:
            return status_code, body_or_gen, resp_headers, fallback_model
        if failure_priority(status_code) > failure_priority(best_failure[0]):
            best_failure = (status_code, body_or_gen, resp_headers)

    return (*best_failure, target_model)


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


@app.get("/v1/logs")
async def get_logs(
    request: Request,
    authorization: str | None = Header(None),
    limit: int = 50,
    offset: int = 0,
    status_code: int | None = None,
    provider: str | None = None,
    billing: str | None = None,
) -> dict[str, Any]:
    verify_master_key(authorization, request=request)
    return audit_db.get_logs(
        limit=limit,
        offset=offset,
        status_code=status_code,
        provider=provider,
        billing=billing,
    )


def _build_dispatch_cfg(
    p_id: str,
    p_cfg: dict[str, Any],
    raw_body: dict[str, Any],
    client_ip: str,
    user_agent: str,
    request: Request,
) -> dict[str, Any]:
    if p_id != "opencode-go":
        return p_cfg
    session_id = derive_session_id(
        raw_body.get("messages") or [],
        client_ip=client_ip,
        user_agent=user_agent,
        provided=request.headers.get(SESSION_HEADER),
    )
    return {
        **p_cfg,
        "extra_headers": {
            **p_cfg.get("extra_headers", {}),
            SESSION_HEADER: session_id,
        },
    }


async def _build_streaming_response(
    *,
    body_or_gen: Any,
    p_id: str,
    p_cfg: dict[str, Any],
    req: ChatCompletionRequest,
    target_model: str,
    elapsed_ms: float,
    start_time: float,
    failover_log: list[str],
    client_ip: str,
    user_agent: str,
    purpose: str | None,
    prompt_preview: str | None,
) -> tuple[StreamingResponse | None, dict[str, Any] | None]:
    primed: list[Any] = []
    upstream: Any | None = None
    produced = False
    try:
        primed, upstream, produced = await prime_sse_stream(body_or_gen)
    except asyncio.CancelledError:
        await close_stream_source(body_or_gen)
        raise
    except Exception:
        await close_stream_source(body_or_gen)
        logger.exception("Provider %s died before the first token", p_id)

    if not produced:
        await close_stream_source(body_or_gen)
        circuit_breaker.record_stream_failure(p_id)
        failover_log.append(f"{p_id} (stream ended before first token)")
        return None, {
            "error": {
                "message": f"{p_id} closed the stream before the first token",
                "type": "stream_truncated",
            }
        }

    def _log_stream(result: dict[str, Any]) -> None:
        usage = result.get("usage") or {}
        if result.get("truncated"):
            circuit_breaker.record_stream_failure(p_id)
        elif not result.get("cancelled"):
            circuit_breaker.record_success(p_id)
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
            billing=str(p_cfg.get("billing") or "free"),
        )

    return (
        StreamingResponse(
            audited_sse_stream(
                prefixed_stream(primed, upstream),
                _log_stream,
                started_at=start_time,
            ),
            media_type="text/event-stream",
        ),
        None,
    )


def _build_json_response(
    *,
    body_or_gen: Any,
    p_id: str,
    p_cfg: dict[str, Any],
    req: ChatCompletionRequest,
    target_model: str,
    elapsed_ms: float,
    failover_log: list[str],
    client_ip: str,
    user_agent: str,
    purpose: str | None,
    prompt_preview: str | None,
) -> JSONResponse:
    circuit_breaker.record_success(p_id)
    normalize_non_streaming_choices(body_or_gen)
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
        billing=str(p_cfg.get("billing") or "free"),
    )
    return JSONResponse(content=body_or_gen, status_code=200)


def _record_candidate_failure(
    p_id: str,
    status_code: int,
    body_or_gen: Any,
    resp_headers: dict[str, str],
    failover_log: list[str],
) -> Any:
    retry_after = resp_headers.get("retry-after") or resp_headers.get("ratelimit-reset")
    circuit_breaker.record_failure(
        p_id, status_code=status_code, retry_after=retry_after
    )
    reason = (
        "empty completion"
        if isinstance(body_or_gen, dict)
        and (body_or_gen.get("error") or {}).get("type") == "empty_completion"
        else f"HTTP {status_code}"
    )
    failover_log.append(f"{p_id} ({reason})")
    return body_or_gen


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

    client_ip, user_agent = extract_client_info(request)
    purpose = extract_purpose(request)
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
    failover_log: list[str] = []
    last_error = None
    paid_started: float | None = None
    metered_dispatches = 0

    def _segment_remaining(is_paid_candidate: bool) -> float:
        """Seconds left in the segment that is currently allowed to spend."""
        if not is_paid_candidate:
            return segment_remaining_s(start_time, config.FREE_PASS_DEADLINE_SECONDS)
        return segment_remaining_s(paid_started, config.PAID_PASS_DEADLINE_SECONDS)

    for p_id, p_cfg in candidate_chain:
        is_paid = p_cfg.get("billing") == "paid"
        if is_paid and paid_started is None:
            paid_started = time.perf_counter()

        if not req.stream and _segment_remaining(is_paid) < MIN_ATTEMPT_SECONDS:
            segment = "paid" if is_paid else "free"
            failover_log.append(f"{p_id} (skipped: {segment} pass deadline exhausted)")
            last_error = last_error or {
                "error": {
                    "message": (
                        f"{p_id} skipped: the {segment} segment budget is spent; "
                        "raise FREE_PASS_DEADLINE_SECONDS / "
                        "PAID_PASS_DEADLINE_SECONDS (0 disables)"
                    ),
                    "type": "timeout_error",
                }
            }
            continue

        headers = (
            {"Authorization": f"Bearer {p_cfg['api_key']}"}
            if p_cfg.get("api_key")
            else {}
        )
        available_models = await discovery.fetch_live_models(
            p_id, p_cfg["base_url"], headers
        )
        target_model, skip_reason, skip_err = resolve_candidate_model(
            router, p_id, p_cfg, req.model, available_models, is_paid=is_paid
        )
        if target_model is None:
            if skip_reason:
                failover_log.append(skip_reason)
            last_error = last_error if last_error is not None else skip_err
            continue

        dispatch_cfg = _build_dispatch_cfg(
            p_id, p_cfg, raw_body, client_ip, user_agent, request
        )
        payload = {**raw_body, "model": target_model}
        if p_id != "strata":
            apply_thinking_params(payload, p_cfg, req.model)
            apply_output_ceiling(payload, p_cfg)

        attempt_models: list[tuple[str, bool]] = (
            opencode_go_attempts(p_cfg, available_models, target_model)
            if p_id == "opencode-go" and not is_explicit_paid_request(req.model, p_id)
            else [(target_model, is_paid and not is_plan_model(p_cfg, target_model))]
        )

        (
            (status_code, body_or_gen, resp_headers),
            answered_model,
            metered_dispatches,
            skip_error,
        ) = await _dispatch_candidate_attempts(
            p_id,
            p_cfg,
            dispatch_cfg,
            payload,
            attempt_models,
            stream=req.stream,
            is_paid=is_paid,
            metered_used=metered_dispatches,
            remaining_fn=lambda is_paid=is_paid: _segment_remaining(is_paid),
            failover_log=failover_log,
        )
        target_model = answered_model or target_model
        last_error = last_error if last_error is not None else skip_error
        if status_code == 0:
            continue

        (
            status_code,
            body_or_gen,
            resp_headers,
            target_model,
        ) = await _cascade_in_provider(
            p_id,
            p_cfg,
            dispatch_cfg,
            payload,
            target_model,
            (status_code, body_or_gen, resp_headers),
            available_models=available_models,
            stream=req.stream,
            remaining_fn=lambda is_paid=is_paid: _segment_remaining(is_paid),
        )

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)
        if status_code != 200:
            last_error = _record_candidate_failure(
                p_id, status_code, body_or_gen, resp_headers, failover_log
            )
            continue

        if req.stream:
            stream_resp, stream_err = await _build_streaming_response(
                body_or_gen=body_or_gen,
                p_id=p_id,
                p_cfg=p_cfg,
                req=req,
                target_model=target_model,
                elapsed_ms=elapsed_ms,
                start_time=start_time,
                failover_log=failover_log,
                client_ip=client_ip,
                user_agent=user_agent,
                purpose=purpose,
                prompt_preview=prompt_preview,
            )
            if stream_resp is not None:
                return stream_resp
            last_error = stream_err
            continue

        return _build_json_response(
            body_or_gen=body_or_gen,
            p_id=p_id,
            p_cfg=p_cfg,
            req=req,
            target_model=target_model,
            elapsed_ms=elapsed_ms,
            failover_log=failover_log,
            client_ip=client_ip,
            user_agent=user_agent,
            purpose=purpose,
            prompt_preview=prompt_preview,
        )

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
