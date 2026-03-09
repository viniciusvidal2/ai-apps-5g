"""Service helpers for REST APIs and streaming responses."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict

from fastapi import HTTPException

from ihm.server import state
from ihm.server.config import SESSION_IDLE_TTL_SECONDS, USE_AI_ASSISTANT
from ihm.server.modules.rest_api_client import (
    kill_ai_assistant_agent,
    start_ai_assistant_agent,
    wait_for_ai_assistant_health,
)

logger = logging.getLogger(__name__)


async def _container_is_reachable() -> bool:
    """Quickly check whether the shared AI Assistant container is reachable."""
    try:
        await wait_for_ai_assistant_health(
            timeout_seconds=8,
            poll_interval_seconds=1.0,
            log_timeout=False,
            context="quick_reachability_probe",
        )
        return True
    except HTTPException:
        return False


def _prune_expired_sessions_locked(source: str) -> list[str]:
    """Drop idle sessions while already holding the shared service lock."""
    expired_session_ids = state.expire_idle_sessions(SESSION_IDLE_TTL_SECONDS)
    if expired_session_ids:
        logger.warning(
            "EXPIRED_IDLE_SESSIONS - source=%s expired_session_ids=%s remaining_active_sessions=%s",
            source,
            expired_session_ids,
            state.count_active_sessions(),
        )
    return expired_session_ids


async def _adopt_running_container_if_needed(user_id: str, session_id: str, source: str) -> bool:
    """Reconcile in-memory state with an already running agent discovered via health."""
    if await _container_is_reachable():
        state.docker_container_running = True
        state.last_user_id = user_id
        logger.warning(
            "RECONCILED_CONTAINER_STATE - source=%s session_id=%s user_id=%s action=adopted_running_agent",
            source,
            session_id,
            user_id,
        )
        return True
    return False


async def _start_container_and_wait_ready(user_id: str, session_id: str) -> None:
    """Start the shared container and wait until health check succeeds."""
    started_at = time.perf_counter()
    await start_ai_assistant_agent(user_id=user_id, session_id=session_id)
    await wait_for_ai_assistant_health(context=f"start_container:{session_id}")
    state.docker_container_running = True
    state.last_user_id = user_id
    logger.info(
        "CONTAINER_READY - session_id=%s user_id=%s duration_ms=%s",
        session_id,
        user_id,
        round((time.perf_counter() - started_at) * 1000, 1),
    )


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

    async with state.service_lock:
        _prune_expired_sessions_locked(source="start_services_if_needed")

        if state.docker_container_running:
            if await _container_is_reachable():
                logger.info("SKIPPING start; shared AI Assistant container is already running")
                return
            logger.warning(
                "Shared container state is stale (flag=true, health unreachable). Restarting..."
            )
            state.docker_container_running = False

        if await _adopt_running_container_if_needed(
            user_id=user_id,
            session_id=session_id,
            source="start_services_if_needed",
        ):
            return

        await _start_container_and_wait_ready(user_id=user_id, session_id=session_id)
        logger.info("SERVICES STARTED - shared container ready")


async def shutdown_services_if_idle(
    session_id: str,
    user_id: str,
    *,
    trigger: str = "unknown",
) -> bool:
    """Stop shared AI Assistant services when no active sessions remain."""
    logger.info(
        "SHUTDOWN_SERVICES - session_id=%s user_id=%s trigger=%s",
        session_id,
        user_id,
        trigger,
    )

    async with state.service_lock:
        _prune_expired_sessions_locked(source=f"shutdown:{trigger}")

        if state.active_sessions:
            log_method = logger.debug if trigger == "background_sweep" else logger.info
            log_method(
                "SKIPPING shutdown; active sessions still present (%s) trigger=%s",
                state.count_active_sessions(),
                trigger,
            )
            return False

        if not state.docker_container_running:
            if not await _adopt_running_container_if_needed(
                user_id=user_id,
                session_id=session_id,
                source=f"shutdown:{trigger}",
            ):
                log_method = logger.debug if trigger == "background_sweep" else logger.info
                log_method(
                    "SKIPPING shutdown; shared container is already stopped trigger=%s",
                    trigger,
                )
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

    async with state.service_lock:
        _prune_expired_sessions_locked(source="ensure_services_ready")

        if state.docker_container_running:
            if await _container_is_reachable():
                logger.info("SERVICES READY - shared container healthy")
                return
            logger.warning(
                "Shared container state is stale during inference (flag=true, health unreachable). Restarting..."
            )
            state.docker_container_running = False

        if await _adopt_running_container_if_needed(
            user_id=user_id,
            session_id=session_id,
            source="ensure_services_ready",
        ):
            logger.info("SERVICES READY - adopted existing healthy agent")
            return

        await _start_container_and_wait_ready(user_id=user_id, session_id=session_id)
        logger.info("SERVICES READY - shared container healthy")


async def sweep_idle_sessions(source: str = "background_sweep") -> list[str]:
    """Expire idle sessions and stop the shared container when nothing is active."""
    should_shutdown = False
    session_id = f"idle-sweep:{source}"
    user_id = state.last_user_id or "1"

    async with state.service_lock:
        expired_session_ids = _prune_expired_sessions_locked(source=source)
        should_shutdown = not state.active_sessions

    if should_shutdown:
        await shutdown_services_if_idle(
            session_id=session_id,
            user_id=user_id,
            trigger=source,
        )

    return expired_session_ids


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
