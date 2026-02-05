
from pydantic import BaseModel


class AiAssistantInputData(BaseModel):
    """A class to validate the input data that creates an AiAssistant agent instance.

    Args:
        BaseModel: _BaseModel_ from pydantic library.
    """
    broker: str
    port: int
    user_id: int
    input_topic: str
    output_topic: str
    inference_model_name: str
    container_name: str


class AiAssistantKillData(BaseModel):
    """A class to validate the input data that kills an AiAssistant agent instance.

    Args:
        BaseModel: _BaseModel_ from pydantic library.
    """
    user_id: int
    container_name: str
