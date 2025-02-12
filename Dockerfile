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
    && rm -rf /var/lib/apt/lists/*

# Update pip
RUN pip install --upgrade pip

# Copy code to inside the image
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

# Copy interesting folders and app file
COPY ai_apis /app/ai_apis
COPY chat_app.py /app/chat_app.py
COPY ollama_models /app/ollama_models

# Install ollama
RUN curl -fsSL https://ollama.com/install.sh | sh
# Set the ollama models custom directory
ENV OLLAMA_MODELS="/app/ollama_models"

# Set the command to run the chat application
EXPOSE 8501
CMD ollama serve & streamlit run --server.port=8501 --server.address=0.0.0.0 chat_app.py
