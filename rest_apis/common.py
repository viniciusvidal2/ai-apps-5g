
from pydantic import BaseModel


class AiAssistantInputData(BaseModel):
    """A class to validate the input data that creates an AiAssistant agent instance.

    Args:
        BaseModel: _BaseModel_ from pydantic library.
    """
    port: int
    db_ip_address: str
    inference_model_name: str
    container_name: str


class AiAssistantKillData(BaseModel):
    """A class to validate the input data that kills an AiAssistant agent instance.

    Args:
        BaseModel: _BaseModel_ from pydantic library.
    """
    container_name: str
