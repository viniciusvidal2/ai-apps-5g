import paho.mqtt.client as mqtt
from typing import Any
import json


class PdfParseAgentTest:
    def __init__(self, pdf_test_path: str = "test.pdf") -> None:
        """Initializes a PdfParseAgentTest object to test the PDF parsing capabilities.
        
        Args:
            pdf_test_path (str): The path to the test PDF file. Defaults to "test.pdf".
        """
        self.pdf_test_path = pdf_test_path
        # Start the MQTT client and connect to the broker
        self.mqtt_address = "localhost"
        self.mqtt_port = 1883
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = 1
        self.input_topic = f"{str(self.user_id)}/pdf/encoded"
        self.output_topic = f"{str(self.user_id)}/pdf/prompt_data"
        # Start the subscriber to listen for incoming parsed PDF messages
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
        # Publishes a test message to the input topic
        with open(self.pdf_test_path, "rb") as pdf_file:
            self.client.publish(self.input_topic, pdf_file.read(), qos=1)
        print(
            f"Connected to MQTT broker at {self.mqtt_address}:{self.mqtt_port} for user id {self.user_id}. Test PDF published to {self.input_topic}"
        )

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback function for when a message is received on the subscribed topic.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            msg (mqtt.MQTTMessage): The received MQTT message.
        """
        print(f"Received message on topic {msg.topic}:")
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        print("PDF data prompts received:")
        print(json.dumps(data, indent=2))
        # disconnect the client after receiving the message
        self.client.disconnect()
        self.client.loop_stop()


if __name__ == "__main__":
    pdf_path = "/home/grin/Downloads/boleto.pdf"
    agent_test = PdfParseAgentTest(pdf_test_path=pdf_path)
    # Keep the script running to listen for messages
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping PDF Parse Agent Test.")
        agent_test.client.disconnect()
        agent_test.client.loop_stop()
