import paho.mqtt.client as mqtt
from typing import Any
import numpy as np
import json
import base64


class NnTrainAgentTest:
    def __init__(self) -> None:
        """Initializes a NnTrainAgentTest object to test neural network training
        """
        # Start the MQTT client and connect to the broker
        self.mqtt_address = "localhost"
        self.mqtt_port = 1883
        self.client = mqtt.Client()
        self.client.connect(self.mqtt_address, self.mqtt_port)
        # Input and output topics are based on the user ID
        self.user_id = 1
        self.input_topic = f"{str(self.user_id)}/nn/train_data"
        self.output_topic = f"{str(self.user_id)}/nn/output_data"
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
        input_data = {
            "feature1": list(np.random.rand(200)),
            "feature2": list(np.random.rand(200)),
        }
        output_data = {
            "target": list(2 * np.array(input_data["feature1"]) + 3 * np.array(input_data["feature2"]) + np.random.randn(200) * 0.1)
        }
        hidden_layers = [64, 32, 16]
        epochs = 10
        lr = 0.001
        batch_size = 16
        # Prepare the message payload
        message = {
            "input_data": input_data,
            "output_data": output_data,
            "hidden_layers": hidden_layers,
            "epochs": epochs,
            "lr": lr,
            "batch_size": batch_size
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
        print(f"Received message on topic {msg.topic}:")
        payload = msg.payload.decode('utf-8')
        data = json.loads(payload)
        # Obtain the serialized model from the message
        model = data.get('model', None)
        if model:
            print("Model received successfully.")
            # Decode the model from base64
            model_bytes = base64.b64decode(model)
            # Here you would typically load the model into your neural network framework
            # For demonstration, we will just print the size of the model
            print(f"Model size: {len(model_bytes)} bytes")
            # You can also save the model to a file or use it directly in your application
            with open("trained_model.pth", "wb") as f:
                f.write(model_bytes)
            print("Model saved to 'trained_model.pth'.")
        else:
            print("No model found in the received message.")


if __name__ == "__main__":
    # Example usage
    agent = NnTrainAgentTest()
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
