FROM ubuntu:22.04 AS base

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-distutils \
    python3-pip \
    curl \
    git \
    nano \
    docker-cli \
    && rm -rf /var/lib/apt/lists/*

# Update pip
RUN pip install --upgrade pip

# Install pip dependencies
RUN pip install --no-cache-dir flask flask_cors pydantic

# Copy common files
COPY rest_apis/common.py /app/common.py

# --- Start Stage ---
FROM base AS start

# Copy start script
COPY rest_apis/start_ai_assistant_agent_docker.py /app/start_ai_assistant_agent_docker.py
RUN chmod +x /app/start_ai_assistant_agent_docker.py /app/common.py

# Expose the REST API port
EXPOSE 8002

# Set the command to run the REST API
CMD ["/app/start_ai_assistant_agent_docker.py"]

# --- Kill Stage ---
FROM base AS kill

# Copy kill script
COPY rest_apis/kill_ai_assistant_agent_docker.py /app/kill_ai_assistant_agent_docker.py
RUN chmod +x /app/kill_ai_assistant_agent_docker.py /app/common.py

# Expose the REST API port
EXPOSE 8003

# Set the command to run the REST API
CMD ["/app/kill_ai_assistant_agent_docker.py"]
