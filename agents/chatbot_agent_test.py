import paho.mqtt.client as mqtt
from typing import Any
import json


class ChatbotAgentTest:
    def __init__(self) -> None:
        """Initializes a ChatbotAgentTest object to test chatbot interactions
        """
        # Start the MQTT client and connect to the broker
        self.mqtt_address = "localhost"
        self.mqtt_port = 1883
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = 1
        self.input_topic = f"{str(self.user_id)}/chatbot/input_data"
        self.output_topic = f"{str(self.user_id)}/chatbot/output_data"
        # Start the subscriber to listen for incoming messages
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        self.client.subscribe(self.output_topic, qos=1)
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
        # Creates input data for testing
        message = {
            "user_input": "Hello, how are you?"
        }
        # Publish the message to the input topic
        self.client.publish(self.input_topic, json.dumps(message), qos=1)

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
        assistant_response = data.get("assistant_response", "")
        if assistant_response:
            print(f"Received response from agent: {assistant_response}")
        else:
            print("No response received from agent.")
        # Stop the MQTT client loop after receiving the message
        self.client.loop_stop()
        self.client.disconnect()

if __name__ == "__main__":
    # Example usage
    agent = ChatbotAgentTest()
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
