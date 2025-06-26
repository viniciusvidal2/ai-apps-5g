import paho.mqtt.client as mqtt
from typing import Any
import argparse
import json
from ai_apis.chat_with_history import ChatBot


class ChatbotAgent:
    def __init__(self, mqtt_address: str, mqtt_port: int, user_id: int, input_topic: str, output_topic: str) -> None:
        """Initializes a ChatbotAgent object to handle chat interactions.

        Args:
            mqtt_address (str): The MQTT broker address.
            mqtt_port (int): The MQTT broker port.
            user_id (int): The user ID associated with the agent.
            input_topic (str): The MQTT topic to subscribe for input data.
            output_topic (str): The MQTT topic to publish output data.
        """
        # Initialize the chat bot instance
        self.chatbot = ChatBot(model_id="deepseek-r1:70b")
        # Start the MQTT client and connect to the broker
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = user_id
        self.input_topic = input_topic
        self.output_topic = output_topic
        # Start the subscriber to listen for incoming messages
        self.client.subscribe(self.input_topic, qos=1)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        # Start the publisher to send messages to the MQTT broker
        self.client.loop_start()

    def on_connect(self, client: mqtt.Client, userdata: Any, flags: dict, rc: int) -> None:
        """Callback function for when the client connects to the MQTT broker.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            flags (dict): Response flags from the broker.
            rc (int): Connection result code.
        """
        print(
            f"Connected to MQTT broker at {self.mqtt_address}:{self.mqtt_port} for user id {self.user_id}")

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback function for when a message is received on the subscribed topic.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            msg (mqtt.MQTTMessage): The received MQTT message.
        """
        # Parse the incoming message payload as JSON
        try:
            data = json.loads(msg.payload.decode('utf-8'))
        except json.JSONDecodeError:
            print("Received message is not valid JSON.")
            return
        # Insert the message into the chatbot and get the response
        assistant_response = ""
        for chunk in self.chatbot.chat(user_input=data["user_input"]):
            assistant_response += chunk
            print(chunk, end="", flush=True)
        # Publish the model data to the MQTT broker
        self.client.publish(
            self.output_topic,
            payload=json.dumps({"assistant_response": assistant_response}),
            qos=1
        )
        # Update the chatbot history with the user input and assistant response
        self.chatbot.updateHistory(
            user_input=data["user_input"],
            assistant_response=assistant_response
        )

    def get_output_topic(self) -> str:
        """Returns the output topic for the PDF data prompts.

        Returns:
            str: The output topic string.
        """
        return self.output_topic

    def stop(self) -> None:
        """Stops the MQTT client and disconnects from the broker."""
        if not self.client.is_connected():
            return
        self.client.loop_stop()
        self.client.disconnect()


def main() -> None:
    """Main function to run the Chatbot agent.
    """
    # Parsing arguments for the MQTT broker address, port, and user ID
    parser = argparse.ArgumentParser(description="MQTT Chatbot agent")
    parser.add_argument(
        "--broker", "-b",
        type=str,
        required=True,
        help="MQTT broker address (e.g., 192.168.1.10)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883)"
    )
    parser.add_argument(
        "--user_id", "-t",
        type=int,
        default="1",
        help="user id"
    )
    parser.add_argument(
        "--input_topic", "-i",
        type=str,
        default="chatbot/input",
        help="MQTT input topic"
    )
    parser.add_argument(
        "--output_topic", "-o",
        type=str,
        default="chatbot/output",
        help="MQTT output topic"
    )
    args = parser.parse_args()
    # Create an instance of the agent with the provided MQTT broker address, port, and user ID
    agent = ChatbotAgent(
        mqtt_address=args.broker,
        mqtt_port=args.port,
        user_id=args.user_id,
        input_topic=args.input_topic,
        output_topic=args.output_topic
    )
    try:
        # Keep the agent running to listen for incoming messages
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping Chatbot agent due to keyboard interrupt.")
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
