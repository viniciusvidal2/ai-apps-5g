from pathlib import Path
from time import time
import os
from ollama import chat


def epiDescriptionFromImage(image_path: str, model_id: str) -> str:
    """Get an instruction EPI description for the workers in a given image, providing the model ID

    Args:
        image_path (str): the image path
        model_id (str): the model id for inference

    Raises:
        FileNotFoundError: If no image is found at the given path

    Returns:
        str: The EPI description for the workers in the image
    """
    # Check if the image exists
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f'Image not found at: {path}')

    # Prepare the message history and get the response
    message_history = [
        {
            'role': 'user',
            'content': 'Analyze the image and tell me how many people are in it. Also, tell me what protection equipment they are wearing and what are missing, from the options: safety glasses, helmets, boots, gloves. Tell it for each person, from left to right. Make the leftmost person number 1, the next person number 2, and so on.',
        },
        {
            'role': 'assistant',
            'content': 'I will do so, by writing a topic for each person in the image. I will also use Portuguese language in my answers.',
        },
        {
            'role': 'user',
            'content': 'This is the image with employees to be analyzed. Do as we discussed. If no person is found, simply say it. Respond in Portuguese.',
            'images': [path],
        },
    ]

    # Get the response from the chatbot
    response = chat(model=model_id, messages=message_history,
                    options={'temperature': 0})
    return response.message.content


if __name__ == "__main__":
    # Run a sample of the script for demonstration purposes
    start = time()
    image_path = os.path.join(os.getenv("$HOME"), "Pictures", "workers.jpeg")
    result = epiDescriptionFromImage(
        image_path=image_path, model_id="llama3.2-vision")
    end = time()
    print("Generated report:\n")
    print(f"{result}")
    print(f"Time elapsed: {end-start:.2f} seconds")
