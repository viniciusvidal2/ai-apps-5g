from __future__ import annotations

"""API routes for the AI Assistant server."""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from ihm.server import state
from ihm.server.config import USE_AI_ASSISTANT
from ihm.server.models import (
    AvailableModelsResponse,
    CollectionsResponse,
    HealthResponse,
    InferenceRequest,
    ServiceRequest,
    ServiceResponse,
)
from ihm.server.modules.rest_api_client import (
    get_ai_assistant_available_models,
    get_ai_assistant_collections,
    get_ai_assistant_conversation_summary,
    get_ai_assistant_health,
    stream_ai_assistant_inference,
)
from ihm.server.modules.services import (
    build_mock_stream,
    ensure_services_ready,
    format_sse_event,
    shutdown_services_if_idle,
    start_services_if_needed,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _truncate_text(value: str, max_chars: int = 160) -> str:
    """Trim request payloads before logging them."""
    normalized = " ".join(value.split())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[: max_chars - 3]}..."


def _request_metadata(request: Request) -> Dict[str, str]:
    """Extract request headers commonly needed for backend debugging."""
    return {
        "origin": request.headers.get("origin", ""),
        "referer": request.headers.get("referer", ""),
        "user_agent": request.headers.get("user-agent", ""),
    }


async def _register_or_touch_session(session_id: str, user_id: str, source: str) -> tuple[int, int]:
    """Track a session entirely on the server side."""
    async with state.service_lock:
        state.register_session(session_id=session_id, user_id=user_id, source=source)
        return (
            state.count_active_sessions(),
            state.count_active_sessions(user_id=user_id),
        )


async def _remove_session(session_id: str, user_id_hint: str) -> tuple[str, int, int]:
    """Remove a session from runtime state and return updated counters."""
    async with state.service_lock:
        session_data = state.remove_session(session_id)
        user_id = (
            session_data["user_id"]
            if session_data
            else user_id_hint or state.last_user_id or "1"
        )
        return (
            user_id,
            state.count_active_sessions(),
            state.count_active_sessions(user_id=user_id),
        )


def _runtime_request_context() -> tuple[str, str]:
    """Provide stable identifiers for service readiness checks outside inference."""
    return (state.last_user_id or "1", "runtime-options")


@router.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Return a simple response to confirm the server is alive."""
    return HealthResponse(status="ok", message="AI Assistant API is working!")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Report service health for Docker and AI Assistant dependencies."""
    if not USE_AI_ASSISTANT:
        return HealthResponse(status="healthy", message="Server working in mock mode")

    active_sessions = state.count_active_sessions()

    if not state.docker_container_running:
        return HealthResponse(
            status="healthy",
            message=f"AI Assistant enabled with no running container ({active_sessions} active session(s))",
        )

    try:
        ai_health = await get_ai_assistant_health()
    except HTTPException as exc:
        return HealthResponse(
            status="warning",
            message=f"AI Assistant container running but unhealthy: {exc.detail}",
        )

    ai_status = ai_health.get("status", "unknown")
    return HealthResponse(
        status="healthy",
        message=(
            f"AI Assistant container running ({active_sessions} active session(s)); "
            f"agent health: {ai_status}"
        ),
    )


@router.get(
    "/ai_assistant/available_models",
    response_model=AvailableModelsResponse,
)
async def available_models() -> AvailableModelsResponse:
    """Proxy the current AI Assistant model list for the browser client."""
    if not USE_AI_ASSISTANT:
        return AvailableModelsResponse(available_models=[])

    user_id, session_id = _runtime_request_context()
    await ensure_services_ready(user_id=user_id, session_id=session_id)
    data = await get_ai_assistant_available_models()

    models = [
        model.strip()
        for model in data.get("available_models", [])
        if isinstance(model, str) and model.strip()
    ]
    return AvailableModelsResponse(available_models=models)


@router.get(
    "/ai_assistant/collections",
    response_model=CollectionsResponse,
)
async def collections() -> CollectionsResponse:
    """Proxy the current AI Assistant collection list for the browser client."""
    if not USE_AI_ASSISTANT:
        return CollectionsResponse(collection_names=[], ready=True)

    user_id, session_id = _runtime_request_context()
    await ensure_services_ready(user_id=user_id, session_id=session_id)
    data = await get_ai_assistant_collections()

    collection_names = [
        collection_name.strip()
        for collection_name in data.get("collection_names", [])
        if isinstance(collection_name, str) and collection_name.strip()
    ]
    return CollectionsResponse(
        collection_names=collection_names,
        ready=bool(data.get("ready", True)),
    )


@router.post("/turn_on_services", response_model=ServiceResponse)
async def turn_on_services(
    service_request: ServiceRequest,
    request: Request,
) -> ServiceResponse:
    """Register a session and start shared services if needed."""
    metadata = _request_metadata(request)
    active_count, user_session_count = await _register_or_touch_session(
        session_id=service_request.session_id,
        user_id=service_request.user_id,
        source="turn_on_services",
    )

    logger.info(
        "TURN_ON_SERVICES REQUEST - user_id=%s session_id=%s active_sessions=%s user_sessions=%s origin=%s referer=%s user_agent=%s payload=%s",
        service_request.user_id,
        service_request.session_id,
        active_count,
        user_session_count,
        metadata["origin"],
        metadata["referer"],
        metadata["user_agent"],
        {
            "session_id": service_request.session_id,
            "user_id": service_request.user_id,
        },
    )

    await start_services_if_needed(
        user_id=service_request.user_id,
        session_id=service_request.session_id,
    )
    return ServiceResponse(
        status="ok",
        message=f"Services started for session {service_request.session_id}",
        active_sessions_count=active_count,
    )


@router.post("/turn_off_services")
async def turn_off_services(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """Remove a session and stop shared services when no sessions remain."""
    metadata = _request_metadata(request)
    try:
        data: Dict[str, str] = {}
        body = await request.body()
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid request body: {exc}")

        session_id = data.get("session_id", "")
        if not session_id:
            raise HTTPException(status_code=400, detail="No session_id provided")

        user_id, active_count, user_session_count = await _remove_session(
            session_id=session_id,
            user_id_hint=data.get("user_id", ""),
        )

        logger.info(
            "TURN_OFF_SERVICES REQUEST - user_id=%s session_id=%s active_sessions=%s user_sessions=%s origin=%s referer=%s user_agent=%s payload=%s",
            user_id,
            session_id,
            active_count,
            user_session_count,
            metadata["origin"],
            metadata["referer"],
            metadata["user_agent"],
            data,
        )

        background_tasks.add_task(
            shutdown_services_if_idle,
            session_id=session_id,
            user_id=user_id,
            trigger="turn_off_services",
        )

        return {
            "status": "ok",
            "message": f"Services shutdown initiated for session {session_id}",
            "active_sessions_count": str(active_count),
            "user_sessions_count": str(user_session_count),
        }
    except Exception as exc:
        logger.warning("Error in turn_off_services (client may have disconnected): %s", exc)
        if "session_id" in locals() and session_id:
            try:
                cleanup_user_id = (
                    user_id
                    if "user_id" in locals()
                    else data.get("user_id", "") or state.last_user_id or "1"
                )
                background_tasks.add_task(
                    shutdown_services_if_idle,
                    session_id=session_id,
                    user_id=cleanup_user_id,
                    trigger="turn_off_services_exception",
                )
            except Exception as cleanup_error:
                logger.error("Error adding cleanup background task: %s", cleanup_error)
        raise


async def _build_ai_assistant_stream(
    inference_request: InferenceRequest,
) -> AsyncGenerator[str, None]:
    """Stream inference chunks in real-time from the AI Assistant NDJSON stream endpoint."""
    message_id = f"ai-{inference_request.session_id}-{id(inference_request)}"
    message_started = False

    if state.inference_lock.locked():
        yield format_sse_event(
            {
                "type": "data-statusMessage",
                "data": "Aguardando outra inferencia em andamento...",
                "transient": True,
            }
        )

    try:
        async with state.inference_lock:
            startup_status = "Iniciando o AI Assistant e verificando serviços."
            logger.info(
                "INFERENCE STATUS OUT - session_id=%s user_id=%s status=%s",
                inference_request.session_id,
                inference_request.user_id,
                startup_status,
            )
            yield format_sse_event(
                {
                    "type": "data-statusMessage",
                    "data": startup_status,
                    "transient": True,
                }
            )

            await ensure_services_ready(
                user_id=inference_request.user_id,
                session_id=inference_request.session_id,
            )

            inference_payload = {
                "query": inference_request.query,
                "conversation_summary": inference_request.conversation_summary,
                "n_chunks": inference_request.n_chunks,
                "collection_name": inference_request.collection_name,
                "inference_model_name": inference_request.inference_model_name,
                "session_id": inference_request.session_id,
            }

            ready_status = "Serviços prontos. Enviando consulta ao AI Assistant."
            logger.info(
                "INFERENCE STATUS OUT - session_id=%s user_id=%s status=%s",
                inference_request.session_id,
                inference_request.user_id,
                ready_status,
            )
            yield format_sse_event(
                {
                    "type": "data-statusMessage",
                    "data": ready_status,
                    "transient": True,
                }
            )

            yield format_sse_event({"type": "start-step"})
            yield format_sse_event({"type": "text-start", "id": message_id})
            message_started = True

            async for msg in stream_ai_assistant_inference(inference_payload):
                msg_type = msg.get("type")

                if msg_type == "chunk":
                    chunk_text = str(msg.get("data", ""))
                    if chunk_text:
                        yield format_sse_event(
                            {"type": "text-delta", "id": message_id, "delta": chunk_text}
                        )
                        # Yield control back to the event loop so Uvicorn can
                        # flush this chunk to the client before the next one.
                        await asyncio.sleep(0)

                elif msg_type == "status":
                    status_text = str(msg.get("status") or msg.get("data", "")).strip()
                    if status_text:
                        logger.info(
                            "INFERENCE STATUS OUT - session_id=%s user_id=%s status=%s",
                            inference_request.session_id,
                            inference_request.user_id,
                            status_text,
                        )
                        yield format_sse_event(
                            {
                                "type": "data-statusMessage",
                                "data": status_text,
                                "transient": True,
                            }
                        )

                elif msg_type == "complete":
                    status_text = str(msg.get("status", "")).strip()
                    if status_text:
                        logger.info(
                            "INFERENCE STATUS OUT - session_id=%s user_id=%s status=%s",
                            inference_request.session_id,
                            inference_request.user_id,
                            status_text,
                        )
                        yield format_sse_event(
                            {
                                "type": "data-statusMessage",
                                "data": status_text,
                                "transient": True,
                            }
                        )
                    latest_summary = await get_ai_assistant_conversation_summary()
                    yield format_sse_event(
                        {"type": "data-conversationSummary", "data": latest_summary}
                    )

                elif msg_type == "error":
                    error_text = str(msg.get("error", "Erro desconhecido na inferencia"))
                    yield format_sse_event(
                        {
                            "type": "data-statusMessage",
                            "data": f"Erro: {error_text}",
                            "transient": True,
                        }
                    )
                    yield format_sse_event(
                        {"type": "text-delta", "id": message_id, "delta": error_text}
                    )

    except HTTPException as exc:
        error_text = str(exc.detail)
        logger.error(
            "INFERENCE STREAM FAILED - session_id=%s user_id=%s detail=%s",
            inference_request.session_id,
            inference_request.user_id,
            error_text,
        )
        if not message_started:
            yield format_sse_event({"type": "start-step"})
            yield format_sse_event({"type": "text-start", "id": message_id})
            message_started = True

        yield format_sse_event(
            {
                "type": "data-statusMessage",
                "data": f"Erro durante inferencia: {error_text}",
                "transient": True,
            }
        )
        yield format_sse_event({"type": "text-delta", "id": message_id, "delta": error_text})

    except Exception as exc:  # pragma: no cover - defensive
        error_text = f"Unexpected inference error: {exc}"
        logger.exception(
            "INFERENCE STREAM FAILED - session_id=%s user_id=%s error=%s",
            inference_request.session_id,
            inference_request.user_id,
            error_text,
        )
        if not message_started:
            yield format_sse_event({"type": "start-step"})
            yield format_sse_event({"type": "text-start", "id": message_id})
            message_started = True

        yield format_sse_event(
            {
                "type": "data-statusMessage",
                "data": "Erro inesperado durante inferencia",
                "transient": True,
            }
        )
        yield format_sse_event({"type": "text-delta", "id": message_id, "delta": error_text})

    finally:
        if message_started:
            yield format_sse_event({"type": "text-end", "id": message_id})
        yield format_sse_event({"type": "finish-step"})
        yield format_sse_event({"type": "finish"})
        yield "data: [DONE]\n\n"


@router.post("/inference")
async def run_inference(
    inference_request: InferenceRequest,
    request: Request,
):
    """Stream inference responses as Server-Sent Events (SSE)."""
    metadata = _request_metadata(request)
    active_count, user_session_count = await _register_or_touch_session(
        session_id=inference_request.session_id,
        user_id=inference_request.user_id,
        source="inference",
    )

    logger.info(
        "INFERENCE REQUEST - user_id=%s session_id=%s active_sessions=%s user_sessions=%s collection_name=%s inference_model_name=%s n_chunks=%s query_chars=%s query_preview=%s conversation_summary_chars=%s conversation_summary_preview=%s origin=%s referer=%s user_agent=%s",
        inference_request.user_id,
        inference_request.session_id,
        active_count,
        user_session_count,
        inference_request.collection_name,
        inference_request.inference_model_name,
        inference_request.n_chunks,
        len(inference_request.query),
        _truncate_text(inference_request.query),
        len(inference_request.conversation_summary),
        _truncate_text(inference_request.conversation_summary),
        metadata["origin"],
        metadata["referer"],
        metadata["user_agent"],
    )

    if USE_AI_ASSISTANT:
        generator = _build_ai_assistant_stream(inference_request)
    else:
        generator = build_mock_stream(inference_request.query)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


__all__ = ["router"]
