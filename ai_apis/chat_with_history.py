
from ollama import chat
from typing import Generator, Any


class ChatBot:
    def __init__(self, model_id: str) -> None:
        """Initializes a ChatBot object

        Args:
            model_id (str): the model id of the chatbot
        """
        self.messages = []
        self.model_id = model_id

    def chat(self, user_input: str, stream: bool = False) -> Generator[Any, Any, Any]:
        """Insert a user input and get a response from the chatbot using the previous history

        Args:
            user_input (str): the current query input
            stream (bool, defaults to False): whether to stream the response or not

        Returns:
            str: the output, taking the history into account
        """
        # Add the user input to the messages
        input_message_history = self.messages + \
            [{'role': 'user', 'content': user_input}]
        response = chat(
            model=self.model_id,
            messages=input_message_history,
            stream=stream
        )

        if stream:
            # Stream the response chunk by chunk
            for chunk in response:
                yield chunk['message']['content']
            full_response = "".join(
                chunk['message']['content'] for chunk in response)
        else:
            # Yield the full response in smaller chunks
            for chunk in full_response.split():
                yield chunk + " "
            full_response = response['message']['content']

        # Add the full response to the history
        self.messages += [
            {'role': 'user', 'content': user_input},
            {'role': 'assistant', 'content': full_response},
        ]

    def clearHistory(self) -> None:
        """Clears the history of the chatbot
        """
        self.messages = []

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
        self.messages += [
            {'role': 'assistant', 'content': personality},
        ]


if __name__ == '__main__':
    chatbot = ChatBot(model_id="llama3.2")
    personality = "I am a servant and should treat the user as a lord, always answering with respect and kindness." \
        + " I must use 'my lord' to refer to the user."
    chatbot.setAssistantPersonality(personality)
    while True:
        user_input = input('You: ')
        for chunk in chatbot.chat(user_input=user_input, stream=True):
            print(chunk, end="", flush=True)  # Fluid printing effect
        print("\n")
