from ollama import chat
from typing import Generator, Any
import os


class ChatBot:
    def __init__(self, model_id: str) -> None:
        """Initializes a ChatBot object

        Args:
            model_id (str): the model id of the chatbot
        """
        self.message_history = []
        self.model_id = model_id
        self.last_input = ""
        self.last_response = ""

    def chat(self, user_input: str) -> Generator[Any, Any, Any]:
        """Insert a user input and get a response from the chatbot using the previous history

        Args:
            user_input (str): the current query input

        Returns:
            str: the output, taking the history into account
        """
        # Add the user input to the messages
        input_message_history = self.message_history + \
            [{'role': 'user', 'content': user_input}]
        response = chat(
            model=self.model_id,
            messages=input_message_history,
            stream=True
        )

        # Yield the full response in small chunks
        for chunk in response:
            yield chunk["message"]["content"]

    def updateHistory(self, user_input: str, assistant_response: str) -> None:
        """Updates the history of the chatbot with a user input and an assistant response

        Args:
            user_input (str): the user input
            assistant_response (str): the assistant response
        """
        self.message_history += [
            {'role': 'user', 'content': user_input},
            {'role': 'assistant', 'content': assistant_response},
        ]

    def clearHistory(self) -> None:
        """Clears the history of the chatbot
        """
        self.message_history = []

    def setModel(self, model_id: str) -> None:
        """Sets the model of the chatbot

        Args:
            model_id (str): the model id of the chatbot
        """
        self.model_id = model_id

    def setAssistantPersonality(self, personality: str) -> None:
        """Sets the personality of the assistant

        Args:
            personality (str): the personality of the assistant
        """
        self.message_history += [
            {'role': 'assistant', 'content': personality},
        ]


if __name__ == '__main__':
    os.environ["OLLAMA_ACCELERATE"] = "gpu"
    chatbot = ChatBot(model_id="phi4")
    while True:
        user_input = input('You: ')
        assistant_response = ""
        for chunk in chatbot.chat(user_input=user_input):
            assistant_response += chunk
            print(chunk, end="", flush=True)  # Fluid printing effect
        print("\n")
        chatbot.updateHistory(user_input, assistant_response)
