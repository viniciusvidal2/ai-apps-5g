
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


class AiAssistantKillData(BaseModel):
    """A class to validate the input data that kills an AiAssistant agent instance.

    Args:
        BaseModel: _BaseModel_ from pydantic library.
    """
    user_id: int


def generate_docker_name(user_id: int) -> str:
    """Generates an unique name for the docker container

    Args:
        user_id (int): The user ID for which to generate the container name.

    Returns:
        str: The generated container name.
    """
    return f"ai_assistant_{user_id}"
