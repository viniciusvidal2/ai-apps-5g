"""HTTP client helpers for the AI Assistant REST APIs."""
from __future__ import annotations

import asyncio
import logging
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

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(AI_ASSISTANT_START_API_URL, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to reach AI Assistant manager at {AI_ASSISTANT_START_API_URL}: {exc}",
        ) from exc

    if response.status_code != 200:
        logger.error(
            "REST API START FAILED - status=%s response=%s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Assistant manager failed to start container "
                f"(status={response.status_code}): {response.text}"
            ),
        )

    logger.info("REST API START SUCCESS - session_id=%s", session_id)


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

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(AI_ASSISTANT_KILL_API_URL, json=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to reach AI Assistant manager at {AI_ASSISTANT_KILL_API_URL}: {exc}",
        ) from exc

    if response.status_code != 200:
        logger.error(
            "REST API KILL FAILED - status=%s response=%s",
            response.status_code,
            response.text,
        )
        raise HTTPException(
            status_code=503,
            detail=(
                "AI Assistant manager failed to stop container "
                f"(status={response.status_code}): {response.text}"
            ),
        )

    logger.info("REST API KILL SUCCESS - session_id=%s", session_id)


async def wait_for_ai_assistant_health(
    timeout_seconds: int | None = None,
    poll_interval_seconds: float | None = None,
) -> None:
    """Wait until the AI Assistant health endpoint responds with HTTP 200."""
    timeout = timeout_seconds or AI_ASSISTANT_HEALTH_TIMEOUT_SECONDS
    interval = poll_interval_seconds or AI_ASSISTANT_POLL_INTERVAL_SECONDS
    deadline = asyncio.get_event_loop().time() + timeout
    health_url = f"{AI_ASSISTANT_API_URL}/health"
    last_error: str | None = None

    while asyncio.get_event_loop().time() < deadline:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(health_url)
            if response.status_code == 200:
                return
            last_error = f"unexpected status code {response.status_code}"
        except httpx.HTTPError as exc:
            last_error = str(exc)

        await asyncio.sleep(interval)

    raise HTTPException(
        status_code=503,
        detail=(
            f"AI Assistant health check timeout after {timeout}s "
            f"({last_error or 'unknown error'})"
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
