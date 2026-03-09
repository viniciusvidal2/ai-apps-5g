from __future__ import annotations

"""Shared runtime state for the FastAPI server."""
import asyncio
import time
from typing import Dict, Optional, TypedDict


class SessionRecord(TypedDict):
    """Runtime metadata for a browser session tracked by the backend."""

    user_id: str
    created_at: float
    last_seen_at: float
    last_source: str


# Maps session_id -> session metadata.
active_sessions: Dict[str, SessionRecord] = {}

# Global flag: we keep a single AI Assistant container for all sessions.
docker_container_running: bool = False

# Serializes container lifecycle operations across concurrent requests.
service_lock = asyncio.Lock()

# Guards inferences to avoid context/status collisions in the shared container.
inference_lock = asyncio.Lock()

last_user_id: Optional[str] = None


def now_timestamp() -> float:
    """Return the current wall-clock timestamp used for session bookkeeping."""
    return time.time()


def register_session(session_id: str, user_id: str, source: str) -> SessionRecord:
    """Create or refresh a tracked session entry."""
    now = now_timestamp()
    existing = active_sessions.get(session_id)
    record: SessionRecord = {
        "user_id": user_id,
        "created_at": existing["created_at"] if existing else now,
        "last_seen_at": now,
        "last_source": source,
    }
    active_sessions[session_id] = record

    global last_user_id
    last_user_id = user_id
    return record


def touch_session(
    session_id: str,
    source: str,
    user_id: Optional[str] = None,
) -> Optional[SessionRecord]:
    """Refresh last-seen metadata for a session, creating it when user_id is provided."""
    existing = active_sessions.get(session_id)
    if existing is None:
        if user_id is None:
            return None
        return register_session(session_id=session_id, user_id=user_id, source=source)

    existing["last_seen_at"] = now_timestamp()
    existing["last_source"] = source
    if user_id:
        existing["user_id"] = user_id
        global last_user_id
        last_user_id = user_id
    return existing


def remove_session(session_id: str) -> Optional[SessionRecord]:
    """Remove a tracked session from runtime state."""
    return active_sessions.pop(session_id, None)


def count_active_sessions(user_id: Optional[str] = None) -> int:
    """Count tracked sessions, optionally filtered by user id."""
    if user_id is None:
        return len(active_sessions)
    return sum(1 for session_data in active_sessions.values() if session_data["user_id"] == user_id)


def expire_idle_sessions(idle_ttl_seconds: int) -> list[str]:
    """Drop sessions that have been idle for at least the configured TTL."""
    now = now_timestamp()
    expired_session_ids = [
        session_id
        for session_id, session_data in active_sessions.items()
        if now - session_data["last_seen_at"] >= idle_ttl_seconds
    ]
    for session_id in expired_session_ids:
        active_sessions.pop(session_id, None)
    return expired_session_ids
