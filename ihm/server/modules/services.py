"""Service helpers for REST APIs and streaming responses."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import HTTPException

from ihm.server import state
from ihm.server.config import USE_AI_ASSISTANT
from ihm.server.modules.rest_api_client import (
    kill_ai_assistant_agent,
    start_ai_assistant_agent,
    wait_for_ai_assistant_health,
)

logger = logging.getLogger(__name__)


async def _container_is_reachable() -> bool:
    """Quickly check whether the shared AI Assistant container is reachable."""
    try:
        await wait_for_ai_assistant_health(timeout_seconds=8, poll_interval_seconds=1.0)
        return True
    except HTTPException:
        return False


async def _start_container_and_wait_ready(user_id: str, session_id: str) -> None:
    """Start the shared container and wait until health check succeeds."""
    await start_ai_assistant_agent(user_id=user_id, session_id=session_id)
    await wait_for_ai_assistant_health()
    state.docker_container_running = True
    state.last_user_id = user_id


async def start_services_if_needed(user_id: str, session_id: str) -> None:
    """Start shared AI Assistant services if they are not running yet."""
    logger.info(
        "START_SERVICES_IF_NEEDED - session_id=%s user_id=%s",
        session_id,
        user_id,
    )

    if not USE_AI_ASSISTANT:
        logger.info("SKIPPING start; USE_AI_ASSISTANT is False")
        return

    if state.docker_container_running:
        if await _container_is_reachable():
            logger.info("SKIPPING start; shared AI Assistant container is already running")
            return
        logger.warning(
            "Shared container state is stale (flag=true, health unreachable). Restarting..."
        )
        state.docker_container_running = False

    await _start_container_and_wait_ready(user_id=user_id, session_id=session_id)
    logger.info("SERVICES STARTED - shared container ready")


async def shutdown_services_if_idle(session_id: str, user_id: str) -> bool:
    """Stop shared AI Assistant services when no active sessions remain."""
    logger.info("SHUTDOWN_SERVICES - session_id=%s user_id=%s", session_id, user_id)

    if state.active_sessions:
        logger.info(
            "SKIPPING shutdown; active sessions still present (%s)",
            len(state.active_sessions),
        )
        return False

    if not state.docker_container_running:
        logger.info("SKIPPING shutdown; shared container is already stopped")
        return False

    try:
        await kill_ai_assistant_agent(user_id=user_id, session_id=session_id)
    finally:
        state.docker_container_running = False

    logger.info("SERVICES STOPPED - shared container stopped")
    return True


async def ensure_services_ready(user_id: str, session_id: str) -> None:
    """Ensure shared AI Assistant services are ready before inference."""
    logger.info("ENSURE_SERVICES_READY - session_id=%s user_id=%s", session_id, user_id)

    if not USE_AI_ASSISTANT:
        logger.info("SKIPPING readiness check; USE_AI_ASSISTANT is False")
        return

    if state.docker_container_running:
        if await _container_is_reachable():
            logger.info("SERVICES READY - shared container healthy")
            return
        logger.warning(
            "Shared container state is stale during inference (flag=true, health unreachable). Restarting..."
        )
        state.docker_container_running = False

    await _start_container_and_wait_ready(user_id=user_id, session_id=session_id)
    logger.info("SERVICES READY - shared container healthy")


async def build_mock_stream(query: str) -> AsyncGenerator[str, None]:
    """Generate a short mock streaming response when the assistant is disabled."""
    message_id = f"mock-{hash(query)}"
    yield format_sse_event({"type": "data-statusMessage", "data": "Modo mock ativo"})
    yield format_sse_event({"type": "start-step"})
    yield format_sse_event({"type": "text-start", "id": message_id})

    for word in "This is an example response from the mock server.".split():
        yield format_sse_event(
            {"type": "text-delta", "id": message_id, "delta": f"{word} "}
        )
        await asyncio.sleep(0.05)

    yield format_sse_event({"type": "text-end", "id": message_id})
    yield format_sse_event({"type": "finish-step"})
    yield format_sse_event({"type": "finish"})
    yield "data: [DONE]\n\n"


def format_sse_event(payload: Dict[str, Any]) -> str:
    """Serialize a JSON payload into a Server-Sent Event string."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
