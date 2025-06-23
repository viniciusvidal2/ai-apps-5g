import paho.mqtt.client as mqtt
from typing import Any
from ai_apis.pdf_lookup import PdfLookup
import argparse
import json


class PdfParseAgent:
    def __init__(self, mqtt_address: str, mqtt_port: int, user_id: int, input_topic: str, output_topic: str) -> None:
        """Initializes a PdfParseAgent object to handle PDF parsing tasks.

        Args:
            mqtt_address (str): The MQTT broker address.
            mqtt_port (int): The MQTT broker port.
            user_id (int): The user ID associated with the agent.
            input_topic (str): The MQTT topic to subscribe for input data.
            output_topic (str): The MQTT topic to publish output data.
        """
        # Start the MQTT client and connect to the broker
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = user_id
        self.input_topic = input_topic
        self.output_topic = output_topic
        # Start the subscriber to listen for incoming encoded pdf messages
        self.client.subscribe(self.input_topic, qos=1)
        self.client.on_message = self.on_message
        self.client.on_connect = self.on_connect
        # Start the publisher to send messages to the MQTT broker
        self.client.loop_start()
        # Initialize the PDF lookup instance
        self.pdf_lookup = PdfLookup()

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
        self.pdf_lookup.set_pdf_bytes(msg.payload)
        self.pdf_lookup.load_pdf()
        data_prompts = self.pdf_lookup.get_pdf_data_prompts()
        # Publish the PDF data prompts to the MQTT broker
        self.client.publish(
            self.output_topic,
            payload=json.dumps(data_prompts),
            qos=1
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
    """Main function to run the PdfParseAgent.
    """
    # Parsing arguments for the MQTT broker address, port, and user ID
    parser = argparse.ArgumentParser(description="MQTT PDF Receiver")
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
        default="pdf/parse/input",
        help="MQTT input topic for PDF data (default: pdf/parse/input)"
    )
    parser.add_argument(
        "--output_topic", "-o",
        type=str,
        default="pdf/parse/output",
        help="MQTT output topic for PDF data prompts (default: pdf/parse/output)"
    )
    args = parser.parse_args()
    # Create an instance of PdfParseAgent with the provided MQTT broker address, port, and user ID
    pdf_agent = PdfParseAgent(
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
        print("Stopping PdfParseAgent due to keyboard interrupt.")
    finally:
        pdf_agent.stop()


if __name__ == "__main__":
    main()
