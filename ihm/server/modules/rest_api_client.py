"""HTTP client helpers for the AI Assistant REST APIs."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from ihm.server.config import (
    AI_ASSISTANT_API_URL,
    AI_ASSISTANT_CONTAINER_NAME,
    AI_ASSISTANT_DB_IP_ADDRESS,
    AI_ASSISTANT_HEALTH_TIMEOUT_SECONDS,
    AI_ASSISTANT_INTERNAL_PORT,
    AI_ASSISTANT_KILL_API_URL,
    AI_ASSISTANT_POLL_INTERVAL_SECONDS,
    AI_ASSISTANT_START_API_URL,
    INFERENCE_MODEL_NAME,
)

logger = logging.getLogger(__name__)


def _coerce_user_id(user_id: str) -> int:
    """Convert a user id string into a stable integer for logging purposes."""
    try:
        return int(user_id)
    except ValueError:
        return abs(hash(user_id)) % (10**8)


def _truncate_for_log(value: str, max_chars: int = 240) -> str:
    """Trim log payloads so terminal output stays readable."""
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3]}..."


def _classify_manager_start_failure(raw_response: str) -> str:
    """Map raw manager failures into stable reason codes for logs."""
    lowered = raw_response.lower()
    if "already in use" in lowered or "already exists" in lowered:
        return "container_already_exists"
    if "port is already allocated" in lowered or "address already in use" in lowered:
        return "port_already_allocated"
    return "manager_rejected_start"


def _classify_manager_kill_failure(raw_response: str) -> str:
    """Map kill failures into stable reason codes for logs."""
    lowered = raw_response.lower()
    if "no such container" in lowered:
        return "container_not_found"
    if "is not running" in lowered:
        return "container_not_running"
    return "manager_rejected_kill"


async def start_ai_assistant_agent(user_id: str, session_id: str) -> None:
    """Request the REST API to start the shared AI Assistant container."""
    coerced_user_id = _coerce_user_id(user_id)
    payload: Dict[str, Any] = {
        "port": AI_ASSISTANT_INTERNAL_PORT,
        "db_ip_address": AI_ASSISTANT_DB_IP_ADDRESS,
        "inference_model_name": INFERENCE_MODEL_NAME,
        "container_name": AI_ASSISTANT_CONTAINER_NAME,
    }

    logger.info(
        "CALLING REST API - START DOCKER | url=%s session_id=%s user_id=%s coerced_user_id=%s container=%s payload=%s",
        AI_ASSISTANT_START_API_URL,
        session_id,
        user_id,
        coerced_user_id,
        AI_ASSISTANT_CONTAINER_NAME,
        payload,
    )
    started_at = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(AI_ASSISTANT_START_API_URL, json=payload)
    except httpx.HTTPError as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
        logger.error(
            "AI Assistant manager start failed | reason=manager_unreachable session_id=%s user_id=%s coerced_user_id=%s container=%s duration_ms=%s url=%s",
            session_id,
            user_id,
            coerced_user_id,
            AI_ASSISTANT_CONTAINER_NAME,
            duration_ms,
            AI_ASSISTANT_START_API_URL,
        )
        logger.error(
            "AI Assistant manager start raw error | session_id=%s error=%s",
            session_id,
            _truncate_for_log(str(exc)),
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Assistant manager is unreachable while trying to start the container "
                f"at {AI_ASSISTANT_START_API_URL}: {exc}"
            ),
        ) from exc

    duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
    if response.status_code != 200:
        raw_response = response.text
        reason = _classify_manager_start_failure(raw_response)
        log_method = logger.warning if reason in {
            "container_already_exists",
            "port_already_allocated",
        } else logger.error
        log_method(
            "AI Assistant manager start failed | reason=%s session_id=%s user_id=%s coerced_user_id=%s container=%s status=%s duration_ms=%s",
            reason,
            session_id,
            user_id,
            coerced_user_id,
            AI_ASSISTANT_CONTAINER_NAME,
            response.status_code,
            duration_ms,
        )
        log_method(
            "AI Assistant manager start raw response | session_id=%s raw_response=%s",
            session_id,
            _truncate_for_log(raw_response),
        )
        if reason in {"container_already_exists", "port_already_allocated"}:
            logger.warning(
                "AI Assistant manager start continuing after recoverable error | session_id=%s next_step=wait_for_health",
                session_id,
            )
            return
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Assistant manager rejected the container start request "
                f"(reason={reason}, status={response.status_code})"
            ),
        )

    logger.info(
        "REST API START SUCCESS - session_id=%s user_id=%s container=%s duration_ms=%s",
        session_id,
        user_id,
        AI_ASSISTANT_CONTAINER_NAME,
        duration_ms,
    )


async def kill_ai_assistant_agent(user_id: str, session_id: str) -> None:
    """Request the REST API to stop the shared AI Assistant container."""
    coerced_user_id = _coerce_user_id(user_id)
    payload = {"container_name": AI_ASSISTANT_CONTAINER_NAME}

    logger.info(
        "CALLING REST API - KILL DOCKER | url=%s session_id=%s user_id=%s coerced_user_id=%s container=%s payload=%s",
        AI_ASSISTANT_KILL_API_URL,
        session_id,
        user_id,
        coerced_user_id,
        AI_ASSISTANT_CONTAINER_NAME,
        payload,
    )
    started_at = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(AI_ASSISTANT_KILL_API_URL, json=payload)
    except httpx.HTTPError as exc:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
        logger.error(
            "AI Assistant manager kill failed | reason=manager_unreachable session_id=%s user_id=%s coerced_user_id=%s container=%s duration_ms=%s url=%s",
            session_id,
            user_id,
            coerced_user_id,
            AI_ASSISTANT_CONTAINER_NAME,
            duration_ms,
            AI_ASSISTANT_KILL_API_URL,
        )
        logger.error(
            "AI Assistant manager kill raw error | session_id=%s error=%s",
            session_id,
            _truncate_for_log(str(exc)),
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Assistant manager is unreachable while trying to stop the container "
                f"at {AI_ASSISTANT_KILL_API_URL}: {exc}"
            ),
        ) from exc

    duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
    if response.status_code != 200:
        raw_response = response.text
        reason = _classify_manager_kill_failure(raw_response)
        log_method = logger.warning if reason == "container_not_found" else logger.error
        log_method(
            "AI Assistant manager kill failed | reason=%s session_id=%s user_id=%s coerced_user_id=%s container=%s status=%s duration_ms=%s",
            reason,
            session_id,
            user_id,
            coerced_user_id,
            AI_ASSISTANT_CONTAINER_NAME,
            response.status_code,
            duration_ms,
        )
        log_method(
            "AI Assistant manager kill raw response | session_id=%s raw_response=%s",
            session_id,
            _truncate_for_log(raw_response),
        )
        if reason == "container_not_found":
            logger.warning(
                "AI Assistant manager kill treating missing container as already stopped | session_id=%s",
                session_id,
            )
            return
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Assistant manager rejected the container stop request "
                f"(reason={reason}, status={response.status_code})"
            ),
        )

    logger.info(
        "REST API KILL SUCCESS - session_id=%s user_id=%s container=%s duration_ms=%s",
        session_id,
        user_id,
        AI_ASSISTANT_CONTAINER_NAME,
        duration_ms,
    )


async def wait_for_ai_assistant_health(
    timeout_seconds: int | None = None,
    poll_interval_seconds: float | None = None,
    *,
    log_timeout: bool = True,
    context: str = "default",
) -> None:
    """Wait until the AI Assistant health endpoint responds with HTTP 200."""
    timeout = timeout_seconds or AI_ASSISTANT_HEALTH_TIMEOUT_SECONDS
    interval = poll_interval_seconds or AI_ASSISTANT_POLL_INTERVAL_SECONDS
    loop = asyncio.get_running_loop()
    started_at = time.perf_counter()
    deadline = loop.time() + timeout
    health_url = f"{AI_ASSISTANT_API_URL}/health"
    last_error: str | None = None

    while loop.time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(health_url)
            if response.status_code == 200:
                return
            last_error = f"unexpected status code {response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)

        await asyncio.sleep(interval)

    duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
    if log_timeout:
        logger.error(
            "AI Assistant health check failed | reason=container_health_timeout context=%s health_url=%s timeout_seconds=%s duration_ms=%s last_error=%s",
            context,
            health_url,
            timeout,
            duration_ms,
            _truncate_for_log(last_error or "unknown error"),
        )
    raise HTTPException(
        status_code=503,
        detail=(
            "AI Assistant container did not become healthy within the expected time "
            f"(reason=container_health_timeout, timeout={timeout}s, last_error={last_error or 'unknown error'})"
        ),
    )


async def get_ai_assistant_health() -> Dict[str, Any]:
    """Return current health payload from AI Assistant."""
    health_url = f"{AI_ASSISTANT_API_URL}/health"
    async with httpx.AsyncClient(timeout=5) as client:
        response = await client.get(health_url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail=f"AI Assistant health endpoint unavailable (status={response.status_code})",
        )
    return response.json()


async def submit_ai_assistant_inference(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Submit an inference request to AI Assistant."""
    inference_url = f"{AI_ASSISTANT_API_URL}/ai_assistant/inference"
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(inference_url, json=payload)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI Assistant inference submit failed ({response.status_code}): {response.text}",
        )
    return response.json()


async def get_ai_assistant_inference(job_id: str) -> Dict[str, Any]:
    """Get current inference status for a job id."""
    inference_url = f"{AI_ASSISTANT_API_URL}/ai_assistant/inference/{job_id}"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(inference_url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI Assistant inference poll failed ({response.status_code}): {response.text}",
        )

    data = response.json()
    if "error" in data:
        raise HTTPException(status_code=404, detail=str(data["error"]))
    return data


async def get_ai_assistant_conversation_summary() -> str:
    """Fetch the latest conversation summary from AI Assistant."""
    summary_url = f"{AI_ASSISTANT_API_URL}/ai_assistant/conversation_summary"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(summary_url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI Assistant summary fetch failed ({response.status_code}): {response.text}",
        )

    data = response.json()
    return str(data.get("conversation_summary", ""))


async def get_ai_assistant_available_models() -> Dict[str, Any]:
    """Fetch the current list of available inference models from AI Assistant."""
    models_url = f"{AI_ASSISTANT_API_URL}/ai_assistant/available_models"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(models_url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI Assistant available models fetch failed ({response.status_code}): {response.text}",
        )
    return response.json()


async def get_ai_assistant_collections() -> Dict[str, Any]:
    """Fetch the current list of ChromaDB collections from AI Assistant."""
    collections_url = f"{AI_ASSISTANT_API_URL}/ai_assistant/collections"
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(collections_url)
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"AI Assistant collections fetch failed ({response.status_code}): {response.text}",
        )
    return response.json()
