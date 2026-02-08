from dataclasses import dataclass
from pydantic import BaseModel


@dataclass(frozen=True)
class AppConfig:
    db_ip_address: str
    inference_model_name: str
    host: str
    port: int


class AiAssistantInferenceRequest(BaseModel):
    """A class to validate the input data for an inference request to the AI assistant.

    Args:
        BaseModel: _BaseModel_ from pydantic library.
    """
    query: str
    conversation_summary: str
    user_id: str
    session_id: str
    n_chunks: int = 3
    collection_name: str = "documents"
    inference_model_name: str = "gemma3:4b"
