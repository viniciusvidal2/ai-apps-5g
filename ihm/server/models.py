from __future__ import annotations

"""Pydantic models used across the FastAPI server."""
from typing import List

from pydantic import BaseModel

from ihm.server.config import INFERENCE_MODEL_NAME


class InferenceRequest(BaseModel):
    """Model for inference requests."""

    query: str
    user_id: str
    session_id: str
    conversation_summary: str = ""
    n_chunks: int = 3
    inference_model_name: str = INFERENCE_MODEL_NAME
    collection_name: str = "none"  # "documents" or "none"


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


class AvailableModelsResponse(BaseModel):
    """Model for available inference models."""

    available_models: List[str]


class CollectionsResponse(BaseModel):
    """Model for available database collections."""

    collection_names: List[str]
    ready: bool
