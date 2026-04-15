import requests
import argparse


def start_ai_assistant_agent(port: int, db_ip_address: str, inference_model_name: str, container_name: str) -> requests.Response:
    """Sends a request to start an AiAssistant agent inside a Docker container.

    Args:
        port (int): The broker port.
        db_ip_address (str): The database IP address for the AiAssistant agent.
        inference_model_name (str): The name of the inference model to use.
        container_name (str): The name of the Docker container.

    Returns:
        requests.Response: The response from the REST API.
    """
    url = "http://localhost:8002/ai_assistant/start_docker"
    payload = {
        "port": port,
        "db_ip_address": db_ip_address,
        "inference_model_name": inference_model_name,
        "container_name": container_name
    }
    response = requests.post(url, json=payload)
    return response


def kill_ai_assistant_agent(container_name: str) -> requests.Response:
    """Sends a request to kill an AiAssistant agent inside a Docker container.

    Args:
        container_name (str): The name of the Docker container to be killed.
    """
    url = "http://localhost:8002/ai_assistant/kill_docker"
    payload = {
        "container_name": container_name
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
            port=8001, db_ip_address="0.0.0.0", inference_model_name="gemma4:latest", container_name="ai_assistant_1"
        )
        print("Start AI Assistant Agent Response:")
    elif args.action == "kill":
        response = kill_ai_assistant_agent(container_name="ai_assistant_1")
        print("Kill AI Assistant Agent Response:")
    print(response.json())


if __name__ == "__main__":
    main()
