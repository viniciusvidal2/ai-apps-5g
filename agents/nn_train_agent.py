import paho.mqtt.client as mqtt
from typing import Any
import argparse
import json
from ai_apis.nn_model_train import NeuralNetworkTrainer


class NnTrainAgent:
    def __init__(self, mqtt_address: str, mqtt_port: int, user_id: int) -> None:
        """Initializes a NnTrainAgent object to handle the neural network training with desired data.

        Args:
            mqtt_address (str): The MQTT broker address.
            mqtt_port (int): The MQTT broker port.
            user_id (int): The user ID associated with the agent.
        """
        # Initialize the engine instance
        self.nn_trainer = NeuralNetworkTrainer()
        # Start the MQTT client and connect to the broker
        self.mqtt_address = mqtt_address
        self.mqtt_port = mqtt_port
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = user_id
        self.input_topic = f"{str(user_id)}/nn/train_data"
        self.output_topic = f"{str(user_id)}/nn/output_data"
        # Start the subscriber to listen for incoming encoded pdf messages
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
        # Extract the data from the message
        input_data = data.get('input_data', {})
        output_data = data.get('output_data', {})
        hidden_layers = data.get('hidden_layers', [32, 16])
        epochs = data.get('epochs', 100)
        lr = data.get('lr', 0.01)
        batch_size = data.get('batch_size', 16)
        self.nn_trainer.set_data(input_data, output_data)
        self.nn_trainer.set_network_shape(hidden_layers=hidden_layers)
        self.nn_trainer.build_model()
        self.nn_trainer.train(epochs=epochs, lr=lr, batch_size=batch_size)
        model = self.nn_trainer.get_serialized_model()  # [str]
        # Serialize the model to send through MQTT
        model_data = {
            'input_data': input_data,
            'output_data': output_data,
            'hidden_layers': hidden_layers,
            'epochs': epochs,
            'lr': lr,
            'batch_size': batch_size,
            'model': model
        }
        # Publish the model data to the MQTT broker
        self.client.publish(
            self.output_topic,
            payload=json.dumps(model_data),
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
    parser = argparse.ArgumentParser(description="MQTT Sheet agent")
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
    args = parser.parse_args()
    # Create an instance of the agent with the provided MQTT broker address, port, and user ID
    agent = NnTrainAgent(
        mqtt_address=args.broker,
        mqtt_port=args.port,
        user_id=args.user_id
    )
    try:
        # Keep the agent running to listen for incoming messages
        while True:
            pass
    except KeyboardInterrupt:
        print("Stopping NnTrainAgent due to keyboard interrupt.")
    finally:
        agent.stop()


if __name__ == "__main__":
    main()
