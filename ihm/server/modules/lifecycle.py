"""Application lifespan management for background services."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from ihm.server import state
from ihm.server.config import USE_AI_ASSISTANT
from ihm.server.modules.rest_api_client import kill_ai_assistant_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Clean up services when the FastAPI server stops."""
    try:
        yield
    finally:
        # Clean up MQTT clients for all sessions
        for session_id, mqtt_client in list(state.session_mqtt_clients.items()):
            try:
                mqtt_client.disconnect()
            except Exception:
                pass  # Ignore errors during shutdown
        state.session_mqtt_clients.clear()
        
        # Stop Docker containers for all sessions
        if USE_AI_ASSISTANT:
            for session_id in list(state.session_docker_containers.keys()):
                session_data = state.active_sessions.get(session_id, {})
                user_id = session_data.get("user_id", state.last_user_id or "1")
                try:
                    await kill_ai_assistant_agent(user_id=user_id, session_id=session_id)
                except Exception:
                    pass  # Ignore errors during shutdown
            state.session_docker_containers.clear()
        
        # Clean up deprecated global variables (backward compatibility)
        if state.mqtt_client_manager:
            try:
                state.mqtt_client_manager.disconnect()
            except Exception:
                pass
            state.mqtt_client_manager = None
        state.docker_container_running = False
        state.active_sessions.clear()
