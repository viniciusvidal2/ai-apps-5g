import paho.mqtt.client as mqtt
from typing import Any
import json
import base64


class SheetParseAgentTest:
    def __init__(self, sheet_test_path: str, input_columns: list, output_columns: list) -> None:
        """Initializes a SheetParseAgentTest object to test the PDF parsing capabilities.

        Args:
            sheet_test_path (str): The path to the test csv file. Defaults to "test.csv".
            input_columns (list): The list of input column names to be used for selection.
            output_columns (list): The list of output column names to be used for selection.
        """
        self.sheet_test_path = sheet_test_path
        self.input_columns = input_columns
        self.output_columns = output_columns
        # Start the MQTT client and connect to the broker
        self.mqtt_address = "localhost"
        self.mqtt_port = 1883
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = 1
        self.input_topic = f"{str(self.user_id)}/sheet/encoded"
        self.output_topic = f"{str(self.user_id)}/sheet/selected_data"
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
        with open(self.sheet_test_path, "rb") as sheet_file:
            sheet_file_bytes = sheet_file.read()
            sheet_file_base64 = base64.b64encode(sheet_file_bytes).decode('utf-8')
            sheet_data = {
                "input_columns": self.input_columns,
                "output_columns": self.output_columns,
                "sheet_data": sheet_file_base64,
                "sheet_name": self.sheet_test_path.split("/")[-1]
            }
            self.client.publish(self.input_topic, json.dumps(sheet_data), qos=1)
        print(
            f"Connected to MQTT broker at {self.mqtt_address}:{self.mqtt_port} for user id {self.user_id}. Test Sheet published to {self.input_topic}"
        )

    def on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Callback function for when a message is received on the subscribed topic.

        Args:
            client (mqtt.Client): The MQTT client instance.
            userdata (Any): User-defined data of any type.
            msg (mqtt.MQTTMessage): The received MQTT message.
        """
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        print("Input and output collumns received:")
        print(json.dumps(data, indent=2))
        # disconnect the client after receiving the message
        self.client.disconnect()
        self.client.loop_stop()


if __name__ == "__main__":
    sheet_path = "/home/vini/Documents/test.csv"
    input_columns = ['x', 'y']
    output_columns = ['z']
    agent_test = SheetParseAgentTest(sheet_test_path=sheet_path,
                                     input_columns=input_columns,
                                     output_columns=output_columns)
    # Keep the script running to listen for messages
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping PDF Parse Agent Test.")
        agent_test.client.disconnect()
        agent_test.client.loop_stop()
