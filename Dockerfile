# Use Python 3.9 as the base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Update pip
RUN pip install --upgrade pip

# Copy code to inside the image
COPY . /app
RUN pip install -r /app/requirements.txt

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Expose the port Streamlit runs on
EXPOSE 8501

# Set the command to run the chat application
CMD ["streamlit", "run", "chat_app.py", "--server.address=0.0.0.0"]
