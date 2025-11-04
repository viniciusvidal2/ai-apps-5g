import requests
import argparse


def start_ai_assistant_agent(broker: str, port: int, user_id: int, input_topic: str, output_topic: str) -> requests.Response:
    """Sends a request to start an AiAssistant agent inside a Docker container.

    Args:
        broker (str): The broker address.
        port (int): The broker port.
        user_id (int): The user ID for the AiAssistant agent.
        input_topic (str): The MQTT input topic.
        output_topic (str): The MQTT output topic.

    Returns:
        requests.Response: The response from the REST API.
    """
    url = "http://localhost:8000/ai_assistant/start_docker"
    payload = {
        "broker": broker,
        "port": port,
        "user_id": user_id,
        "input_topic": input_topic,
        "output_topic": output_topic
    }
    response = requests.post(url, json=payload)
    return response


def kill_ai_assistant_agent(user_id: int) -> requests.Response:
    """Sends a request to kill an AiAssistant agent inside a Docker container.

    Args:
        user_id (int): The user ID of the AiAssistant agent to be killed.
    """
    url = "http://localhost:8001/ai_assistant/kill_docker"
    payload = {
        "user_id": user_id
    }
    response = requests.post(url, json=payload)
    return response


def main():
    """Run tests for start and for kill of the docker container using the REST APIs"""
    parser = argparse.ArgumentParser(
        description="Test AI Assistant Docker API")
    parser.add_argument(
        "--action", choices=["start", "kill"], required=True, help="Action to perform")
    args = parser.parse_args()

    if args.action == "start":
        response = start_ai_assistant_agent(
            broker="0.0.0.0", port=1883, user_id=1, input_topic="input/topic", output_topic="output/topic")
        print("Start AI Assistant Agent Response:")
    elif args.action == "kill":
        response = kill_ai_assistant_agent(user_id=1)
        print("Kill AI Assistant Agent Response:")
    print(response.json())


if __name__ == "__main__":
    main()
