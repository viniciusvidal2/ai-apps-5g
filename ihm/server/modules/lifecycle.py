"""Application lifespan management for background services."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI

from ihm.server import state
from ihm.server.config import SESSION_SWEEP_INTERVAL_SECONDS, USE_AI_ASSISTANT
from ihm.server.modules.services import shutdown_services_if_idle, sweep_idle_sessions

logger = logging.getLogger(__name__)


async def _idle_session_sweeper() -> None:
    """Periodically expire idle sessions and stop the shared container when needed."""
    while True:
        await asyncio.sleep(SESSION_SWEEP_INTERVAL_SECONDS)
        try:
            await sweep_idle_sessions(source="background_sweep")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Idle session sweep failed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Clean up services when the FastAPI server stops."""
    sweeper_task: Optional[asyncio.Task[None]] = None
    try:
        if USE_AI_ASSISTANT:
            await sweep_idle_sessions(source="startup_reconcile")
            sweeper_task = asyncio.create_task(_idle_session_sweeper())
        yield
    finally:
        if sweeper_task is not None:
            sweeper_task.cancel()
            try:
                await sweeper_task
            except asyncio.CancelledError:
                pass

        user_id = state.last_user_id or "1"
        state.active_sessions.clear()

        # Stop shared Docker container when server shuts down.
        if USE_AI_ASSISTANT:
            try:
                await shutdown_services_if_idle(
                    session_id="shutdown",
                    user_id=user_id,
                    trigger="lifespan_shutdown",
                )
            except Exception as exc:  # pragma: no cover - defensive cleanup
                logger.warning("Error while stopping AI Assistant on shutdown: %s", exc)
            finally:
                state.docker_container_running = False
