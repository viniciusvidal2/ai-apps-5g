import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from typing import Any
import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from ai_apis.ai_assistant import AiAssistant


class AiAssistantAgent:
    def __init__(self, mqtt_address: str, mqtt_port: int, user_id: int, input_topic: str, output_topic: str, inference_model_name: str) -> None:
        """Initializes a AiAssistantAgent object to handle user requests.

        Args:
            mqtt_address (str): The MQTT broker address.
            mqtt_port (int): The MQTT broker port.
            user_id (int): The user ID associated with the agent.
            input_topic (str): The MQTT topic to subscribe for input data.
            output_topic (str): The MQTT topic to publish output data.
            inference_model_name (str): The name of the inference model to use.
        """
        # Initialize the AI Assistant
        print("Initializing AI Assistant...")
        self.ai_assistant = AiAssistant(
            embedding_model_name="qwen3-embedding:latest",
            inference_model_name=inference_model_name,
            documents_db_path="./dbs/chroma_documents_db",
            url_db_path="./dbs/chroma_url_db",
            collection_name="dev_collection"
        )
        # Storing model name so we can check later if we need to switch models
        self.current_inference_model_name = inference_model_name
        # Start the MQTT client and connect to the broker
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION2)
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = user_id
        self.input_topic = input_topic
        self.output_topic = output_topic
        # Executor to handle incoming messages concurrently
        self.executor = ThreadPoolExecutor()
        # Start the subscriber to listen for incoming messages
        self.client.subscribe(self.input_topic, qos=1)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
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

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback function for when a message is received on the subscribed topic.
        What we can expect in the message:
            n_chunks (int): top n most likely chunks of data to retrieve from each requested database
            use_db (bool): use the documents db or not in the query
            use_history (bool): use the history or not in the query
            use_url (bool): use the urls db or not in the query
            query (str): actual query from the user

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
        # Handle the incoming message in a separate thread
        self.executor.submit(self.handle_incoming_message, data)

    def handle_incoming_message(self, data: dict) -> None:
        """Handles an incoming message by sending it to the AI Assistant and publishing the response.

        Args:
            data (dict): The parsed JSON data from the incoming message.
        """
        # Set the chunking parameters
        self.ai_assistant.set_chunks_to_retrieve(
            n_chunks=data.get("n_chunks", 3))
        # Sending the query to the agent for testing
        response_data = self.ai_assistant.run_inference_pipeline(user_query=data.get("query", "Any"),
                                                                 search_db=data.get(
                                                                     "search_db", True),
                                                                 search_urls=data.get(
                                                                     "search_urls", False),
                                                                 use_history=data.get(
                                                                     "use_history", True),
                                                                 )
        # Checking if we need to switch models
        if data.get("inference_model_name", self.current_inference_model_name) != self.current_inference_model_name:
            print("Switching inference model...")
            self.ai_assistant.set_assistant_model(
                data["inference_model_name"])
            self.current_inference_model_name = data["inference_model_name"]

        # Preparing the output for the user with all necessary information
        document_sources = [
            {"document": doc.get('source', 'Unknown'), "page": {doc.get('page', 'N/A')}} for doc in response_data["history_sources"]
        ]
        url_sources = [
            {"title": doc.metadata.get('title', 'Unknown'), "url": doc.metadata.get('source', 'Unknown')} for doc in response_data["urls_used"]
        ]
        output_dict = {
            "answer": response_data["answer"],
            "document_sources": [],
            "url_sources": []
        }
        # Publish the response to the MQTT broker
        self.client.publish(
            self.output_topic,
            payload=json.dumps(output_dict),
            qos=2
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
        # Terminate the AI Assistant models from execution as well
        self.ai_assistant.close_assistant()


def main() -> None:
    """Main function to run the Chatbot agent.
    """
    # Parsing arguments for the MQTT broker address, port, and user ID
    parser = argparse.ArgumentParser(description="MQTT Chatbot agent")
    parser.add_argument(
        "--broker", "-b",
        type=str,
        default="localhost",
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
        default=1,
        help="user id"
    )
    parser.add_argument(
        "--input_topic", "-i",
        type=str,
        default="input",
        help="MQTT input topic"
    )
    parser.add_argument(
        "--output_topic", "-o",
        type=str,
        default="output",
        help="MQTT output topic"
    )
    parser.add_argument(
        "--inference_model_name", "-m",
        type=str,
        default="gemma3:4b",
        help="Name of the inference model to use"
    )
    args = parser.parse_args()
    # Create an instance of the agent with the provided MQTT broker address, port, and user ID
    agent = AiAssistantAgent(
        mqtt_address=args.broker,
        mqtt_port=args.port,
        user_id=args.user_id,
        input_topic=args.input_topic,
        output_topic=args.output_topic,
        inference_model_name=args.inference_model_name
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
