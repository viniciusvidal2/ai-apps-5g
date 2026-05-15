from pydantic import BaseModel
from typing import List, Optional
from dataclasses import dataclass

@dataclass(frozen=True)
class AppConfig:
    data_yaml_path: str
    output_folder: str
    host: str
    port: int

class MedicalDocsInferenceRequest(BaseModel):
    """Input data for a medical document classification request."""
    document_paths: List[str]
    ocr_method: Optional[str] = "paddle"
    classification_model: Optional[str] = "gemma4:e2b"
