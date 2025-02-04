
from ollama import chat


class ChatBot:
    def __init__(self, model_id: str) -> None:
        """Initializes a ChatBot object

        Args:
            model_id (str): the model id of the chatbot
        """
        self.messages = []
        self.model_id = model_id

    def chat(self, user_input: str) -> str:
        """Insert a user input and get a response from the chatbot using the previous history

        Args:
            user_input (str): the current query input

        Returns:
            str: the output, taking the history into account
        """
        # Add the user input to the messages
        input_message_history = self.messages + \
            [{'role': 'user', 'content': user_input}]
        response = chat(
            model=self.model_id,
            messages=input_message_history
        )

        # Add the response to the messages to maintain the history
        self.messages += [
            {'role': 'user', 'content': user_input},
            {'role': 'assistant', 'content': response.message.content},
        ]
        # Return the response
        return response.message.content

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


if __name__ == '__main__':
    chatbot = ChatBot(model_id="llama3.2")
    while True:
        user_input = input('You: ')
        print('Bot:', chatbot.chat(user_input=user_input))
