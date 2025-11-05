import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from typing import Any
import json


class AiAssistantAgentTest:
    def __init__(self) -> None:
        """Initializes a AiAssistantAgentTest object to test assistant interactions
        """
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
            "query": "Hello, how are you?",
            "search_db": False,
            "search_urls": False,
            "use_history": False,
            "n_chunks": 1,
        }
        # Publish the message to the assistant input topic
        self.client.publish(self.input_topic, json.dumps(message), qos=2)

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback function for when a message is received on the subscribed topic.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            msg (mqtt.MQTTMessage): The received MQTT message.
        """
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        # Obtain the agent response from the message payload
        assistant_response = data.get("answer", "")
        document_sources = data.get("document_sources", [])
        url_sources = data.get("url_sources", [])
        if assistant_response:
            print(f"Received response from agent: {assistant_response}")
            print("\nDocument sources:\n")
            for source in document_sources:
                print("")
            print("\nURL sources:\n")
            for source in url_sources:
                print("")
        else:
            print("No response received from agent.")


if __name__ == "__main__":
    # Example usage
    agent = AiAssistantAgentTest()
    try:
        # Keep the script running to listen for messages
        while True:
            pass
    except KeyboardInterrupt:
        print("Exiting...")
        agent.client.loop_stop()
        agent.client.disconnect()
    except Exception as e:
        print(f"An error occurred: {e}")
        agent.client.loop_stop()
        agent.client.disconnect()
    finally:
        print("MQTT client disconnected.")
        agent.client.loop_stop()
        agent.client.disconnect()
        print("Agent stopped.")
        agent = None
