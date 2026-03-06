"""Shared runtime state for the FastAPI server."""
import asyncio
from typing import Any, Dict, Optional

# Maps session_id -> {"user_id": str}
active_sessions: Dict[str, Dict[str, Any]] = {}

# Global flag: we keep a single AI Assistant container for all sessions.
docker_container_running: bool = False

# Serializes container lifecycle operations across concurrent requests.
service_lock = asyncio.Lock()

# Guards inferences to avoid context/status collisions in the shared container.
inference_lock = asyncio.Lock()

last_user_id: Optional[str] = None
