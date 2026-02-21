"""Application lifespan management for background services."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ihm.server import state
from ihm.server.config import USE_AI_ASSISTANT
from ihm.server.modules.rest_api_client import kill_ai_assistant_agent

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Clean up services when the FastAPI server stops."""
    try:
        yield
    finally:
        # Stop shared Docker container when server shuts down.
        if USE_AI_ASSISTANT and state.docker_container_running:
            user_id = state.last_user_id or "1"
            try:
                await kill_ai_assistant_agent(user_id=user_id, session_id="shutdown")
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Error while stopping AI Assistant on shutdown: %s", exc)
            finally:
                state.docker_container_running = False

        state.active_sessions.clear()
