#!/bin/bash

# Start ollama in the background
ollama serve &

# Optional: wait for ollama to start
sleep 2

# Now run your Python module, passing ALL arguments
python3 -m agents.chatbot_agent "$@"
