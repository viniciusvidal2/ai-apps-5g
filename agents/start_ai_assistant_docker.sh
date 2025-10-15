#!/bin/bash

# Start ollama in the background
ollama serve &

# Optional: wait for ollama to start
sleep 5

# Now run your Python module, passing ALL arguments
cd /app
python3 -m agents.ai_assistant_agent "$@"
