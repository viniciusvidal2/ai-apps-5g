import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from typing import Any
import json
from time import time
from random import randint


class AiAssistantAgentTest:
    def __init__(self) -> None:
        """Initializes a AiAssistantAgentTest object to test assistant interactions
        """
        # Available models that we can test
        self.available_models = ["gemma3:4b", "gemma3:12b", "gemma3:27b"]
        # Start the MQTT client and connect to the broker
        self.mqtt_address = "0.0.0.0"
        self.mqtt_port = 1883
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2)
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = 1
        self.input_topic = f"input"
        self.output_topic = f"output"
        # Start the subscriber to listen for incoming messages
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.subscribe(self.output_topic, qos=2)
        # Count time between messages
        self.last_message_time = time()
        # Start the publisher to send messages to the MQTT broker
        self.client.loop_start()

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int, properties=None) -> None:
        """Callback function for when the client connects to the MQTT broker.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            flags (dict): Response flags from the broker.
            rc (int): Connection result code.
            properties: MQTT v5.0 properties (optional).
        """
        print(
            f"Connected to MQTT broker at {self.mqtt_address}:{self.mqtt_port} for user id {self.user_id}")
        # Creates data for testing
        message = {
            "query": "O que acontece quando um fornecedor obtém um IDF inferior a 70? Cite o documento na base de dados em que isso se encontra.",
            "n_chunks": 10,
            "inference_model_name": self.choose_random_model(),
            "vectorstore_name": "documents"
        }
        # Publish the message to the assistant input topic
        self.client.publish(self.input_topic, json.dumps(message), qos=2)
        self.last_message_time = time()

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback function for when a message is received on the subscribed topic.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            msg (mqtt.MQTTMessage): The received MQTT message.
        """
        print("\n\n\n-------------------------------- New message received from agent --------------------------------\n\n\n")
        # Update time since last message
        current_time = time()
        time_diff = current_time - self.last_message_time
        print(f"Time since last message: {time_diff:.2f} seconds")
        self.last_message_time = current_time
        # Parse the incoming message payload as JSON
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        # Obtain the agent response from the message payload
        assistant_response = data.get("answer", "")
        if assistant_response:
            print(f"Received response from agent: {assistant_response}")
        else:
            print("No response received from agent.")
        # Sends a new message to the agent for testing
        message = {
            "query": "Quais são os compromissos da Santo Antônio Energia em relação à saúde, segurança e meio ambiente?",
            "n_chunks": 10,
            "inference_model_name": self.choose_random_model(),
            "vectorstore_name": "documents"
        }
        # Publish the message to the assistant input topic
        self.client.publish(self.input_topic, json.dumps(message), qos=2)

    def choose_random_model(self) -> str:
        """Chooses a random model from the available models.

        Returns:
            str: The name of the randomly selected model.
        """
        model_index = randint(0, len(self.available_models) - 1)
        model_name = self.available_models[model_index]
        print(f"Model chosen for tests: {model_name}")
        return model_name

    def close(self) -> None:
        """Cleans up the MQTT client and stops the agent.
        """
        self.client.loop_stop()
        self.client.disconnect()
        print("Test Agent stopped.")


if __name__ == "__main__":
    # Example usage
    agent = AiAssistantAgentTest()
    try:
        # Keep the script running to listen for messages
        while True:
            pass
    except KeyboardInterrupt:
        print("Exiting...")
        agent.close()
    except Exception as e:
        print(f"An error occurred: {e}")
        agent.close()
    finally:
        print("MQTT client disconnected.")
        agent.close()
        agent = None
