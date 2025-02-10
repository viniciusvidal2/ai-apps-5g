from ollama import Client


def createPersonalizedModel(original_id: str, new_id: str, personality: str) -> None:
    """Creates a personalized model based on an original model with a given personality

    Args:
        original_id (str): the id of the original model
        new_id (str): the id of the new model
        personality (str): the personality of the new model
    """
    client = Client()
    response = client.create(
        model=new_id,
        from_=original_id,
        system=personality,
        stream=False,
    )
    print(response.status)


if __name__ == "__main__":
    original_model_id = "llama3.2"
    generated_model_id = "grin-assistant"
    # Desired personality of the assistant
    personality = "I am a servant and should treat the user as a lord, always answering with respect and kindness." \
        + " I must use 'my lord' to refer to the user."
    # Create and save the model
    createPersonalizedModel(original_id=original_model_id,
                            new_id=generated_model_id, personality=personality)
