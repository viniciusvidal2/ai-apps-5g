#!/usr/bin/env python3
from flask import Flask, request, jsonify
from pydantic import ValidationError, Extra
import subprocess
from common import AiAssistantInputData, generate_docker_name


app = Flask(__name__)


@app.route("/ai_assistant/start_docker", methods=["POST"])
def start_ai_assistant_agent_docker():
    """Starts an AiAssistant agent inside a Docker container based on the provided input data."""
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({"error": "Malformed JSON"}), 400

    # Validate input data
    try:
        input_data = AiAssistantInputData(**data)
    except ValidationError as e:
        return jsonify({"error": "Invalid input data", "details": e.errors()}), 400

    # Create a name for the Docker container with the user id
    container_name = generate_docker_name(input_data.user_id)

    # Call the docker with the provided parameters
    try:
        command = [
            "docker", "run", "-d", "--network=host",
            "--name", container_name,
            "ai_assistant_image",
            f"--broker={input_data.broker}",
            f"--port={input_data.port}",
            f"--user_id={input_data.user_id}",
            f"--input_topic={input_data.input_topic}",
            f"--output_topic={input_data.output_topic}",
            f"--inference_model_name={input_data.inference_model_name}"
        ]
        # command = ["docker", "run", "-d","--network=host", "--name", "ai_assistant_1", "ai_assistant_image", "--broker=0.0.0.0", "--port=1883", "--user_id=1", "--input_topic=input", "--output_topic=output", "--inference_model_name=gemma3:4b"]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        return jsonify({"error": "Failed to start Docker container", "details": e.stderr}), 500

    return jsonify({"message": "Docker container started successfully", "output": result.stdout}), 200


if __name__ == "__main__":
    # listen on all interfaces so it's reachable from containers/other hosts
    app.run(host="0.0.0.0", port=8002, debug=False)
