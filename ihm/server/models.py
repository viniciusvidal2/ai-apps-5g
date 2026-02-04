"""Pydantic models used across the FastAPI server."""
from pydantic import BaseModel


class InferenceRequest(BaseModel):
    """Model for inference requests."""

    query: str
    user_id: str
    session_id: str
    n_chunks: int = 3
    inference_model_name: str = "gemma3:4b"
    vectorstore_name: str = "none"  # "documents" or "none"


class InferenceResponse(BaseModel):
    """Model for inference responses."""

    answer: str
    history_sources: list


class HealthResponse(BaseModel):
    """Model for health check response."""

    status: str
    message: str


class ServiceRequest(BaseModel):
    """Model for service lifecycle requests."""

    session_id: str
    user_id: str


class ServiceResponse(BaseModel):
    """Model for service lifecycle responses."""

    status: str
    message: str
    active_sessions_count: int
