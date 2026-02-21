"""API routes for the AI Assistant server."""
import asyncio
import json
import logging
from typing import AsyncGenerator, Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse

from ihm.server import state
from ihm.server.config import AI_ASSISTANT_POLL_INTERVAL_SECONDS, USE_AI_ASSISTANT
from ihm.server.models import (
    HealthResponse,
    InferenceRequest,
    ServiceRequest,
    ServiceResponse,
)
from ihm.server.modules.rest_api_client import (
    get_ai_assistant_conversation_summary,
    get_ai_assistant_health,
    get_ai_assistant_inference,
    submit_ai_assistant_inference,
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


@router.get("/", response_model=HealthResponse)
async def root() -> HealthResponse:
    """Return a simple response to confirm the server is alive."""
    return HealthResponse(status="ok", message="AI Assistant API is working!")


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Report service health for Docker and AI Assistant dependencies."""
    if not USE_AI_ASSISTANT:
        return HealthResponse(status="healthy", message="Server working in mock mode")

    active_sessions = len(state.active_sessions)

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


@router.post("/turn_on_services", response_model=ServiceResponse)
async def turn_on_services(request: ServiceRequest) -> ServiceResponse:
    """Register a session and start shared services if needed."""
    state.active_sessions[request.session_id] = {"user_id": request.user_id}
    state.last_user_id = request.user_id
    active_count = len(state.active_sessions)

    user_session_count = sum(
        1
        for session_data in state.active_sessions.values()
        if session_data.get("user_id") == request.user_id
    )

    logger.info(
        "SESSION STARTED - user_id=%s session_id=%s active_sessions=%s user_sessions=%s",
        request.user_id,
        request.session_id,
        active_count,
        user_session_count,
    )

    await start_services_if_needed(user_id=request.user_id, session_id=request.session_id)
    return ServiceResponse(
        status="ok",
        message=f"Services started for session {request.session_id}",
        active_sessions_count=active_count,
    )


@router.post("/turn_off_services")
async def turn_off_services(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, str]:
    """Remove a session and stop shared services when no sessions remain."""
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

        session_data = state.active_sessions.pop(session_id, None)
        user_id = session_data.get("user_id") if session_data else state.last_user_id or "1"
        active_count = len(state.active_sessions)

        user_session_count = sum(
            1
            for active_session_data in state.active_sessions.values()
            if active_session_data.get("user_id") == user_id
        )

        logger.info(
            "SESSION ENDED - user_id=%s session_id=%s active_sessions=%s user_sessions=%s",
            user_id,
            session_id,
            active_count,
            user_session_count,
        )

        background_tasks.add_task(
            shutdown_services_if_idle,
            session_id=session_id,
            user_id=user_id,
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
                background_tasks.add_task(
                    shutdown_services_if_idle,
                    session_id=session_id,
                    user_id=user_id,
                )
            except Exception as cleanup_error:
                logger.error("Error adding cleanup background task: %s", cleanup_error)
        raise


async def _build_ai_assistant_stream(
    request: InferenceRequest,
) -> AsyncGenerator[str, None]:
    """Stream inference status and final answer from AI Assistant HTTP polling."""
    message_id = f"ai-{request.session_id}-{id(request)}"
    message_started = False

    if state.inference_lock.locked():
        yield format_sse_event(
            {
                "type": "data-statusMessage",
                "data": "Aguardando outra inferencia em andamento...",
            }
        )

    try:
        async with state.inference_lock:
            await ensure_services_ready(user_id=request.user_id, session_id=request.session_id)

            inference_payload = {
                "query": request.query,
                "conversation_summary": request.conversation_summary,
                "n_chunks": request.n_chunks,
                "collection_name": request.collection_name,
                "inference_model_name": request.inference_model_name,
                "session_id": request.session_id,
            }

            yield format_sse_event(
                {
                    "type": "data-statusMessage",
                    "data": "Enviando consulta para o AI Assistant...",
                }
            )

            submit_data = await submit_ai_assistant_inference(inference_payload)
            job_id = submit_data.get("job_id")
            if not job_id:
                raise HTTPException(status_code=502, detail="AI Assistant did not return job_id")

            initial_status = str(submit_data.get("status_message", "Inferencia iniciada"))
            yield format_sse_event({"type": "data-statusMessage", "data": initial_status})

            yield format_sse_event({"type": "start-step"})
            yield format_sse_event({"type": "text-start", "id": message_id})
            message_started = True

            last_status_message = initial_status
            final_response = ""

            while True:
                poll_data = await get_ai_assistant_inference(str(job_id))
                status = str(poll_data.get("status", "running"))
                status_message = str(poll_data.get("status_message", "")).strip()

                if status_message and status_message != last_status_message:
                    yield format_sse_event(
                        {"type": "data-statusMessage", "data": status_message}
                    )
                    last_status_message = status_message

                if status == "running":
                    yield ": heartbeat\n\n"
                    await asyncio.sleep(AI_ASSISTANT_POLL_INTERVAL_SECONDS)
                    continue

                final_response = str(poll_data.get("response", ""))
                break

            for word in final_response.split():
                yield format_sse_event(
                    {"type": "text-delta", "id": message_id, "delta": f"{word} "}
                )
                await asyncio.sleep(0.02)

            latest_summary = await get_ai_assistant_conversation_summary()
            yield format_sse_event(
                {"type": "data-conversationSummary", "data": latest_summary}
            )

    except HTTPException as exc:
        error_text = str(exc.detail)
        if not message_started:
            yield format_sse_event({"type": "start-step"})
            yield format_sse_event({"type": "text-start", "id": message_id})
            message_started = True

        yield format_sse_event(
            {"type": "data-statusMessage", "data": f"Erro durante inferencia: {error_text}"}
        )
        yield format_sse_event({"type": "text-delta", "id": message_id, "delta": error_text})

    except Exception as exc:  # pragma: no cover - defensive
        error_text = f"Unexpected inference error: {exc}"
        logger.exception(error_text)
        if not message_started:
            yield format_sse_event({"type": "start-step"})
            yield format_sse_event({"type": "text-start", "id": message_id})
            message_started = True

        yield format_sse_event(
            {"type": "data-statusMessage", "data": "Erro inesperado durante inferencia"}
        )
        yield format_sse_event({"type": "text-delta", "id": message_id, "delta": error_text})

    finally:
        if message_started:
            yield format_sse_event({"type": "text-end", "id": message_id})
        yield format_sse_event({"type": "finish-step"})
        yield format_sse_event({"type": "finish"})
        yield "data: [DONE]\n\n"


@router.post("/inference")
async def run_inference(request: InferenceRequest):
    """Stream inference responses as Server-Sent Events (SSE)."""
    if USE_AI_ASSISTANT:
        generator = _build_ai_assistant_stream(request)
    else:
        generator = build_mock_stream(request.query)

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
