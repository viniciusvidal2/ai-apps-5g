FROM ubuntu:22.04

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

# Copy application files
COPY rest_apis/common.py /app/common.py
COPY rest_apis/ai_assistant_manager_api.py /app/ai_assistant_manager_api.py

# Ensure scripts are executable
RUN chmod +x /app/ai_assistant_manager_api.py /app/common.py

# Expose the REST API port
EXPOSE 8002

# Set the command to run the REST API
CMD ["python3", "/app/ai_assistant_manager_api.py"]
