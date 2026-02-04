#!/bin/bash
set -e

# Ensure local Ollama setup (self-contained)
export OLLAMA_MODELS=/app/ollama_models
export OLLAMA_HOST=127.0.0.1
export OLLAMA_PORT=11434

# Start Ollama server in background (internal only)
echo "Starting Ollama server..."
ollama serve > /var/log/ollama.log 2>&1 &

# Wait until Ollama API responds
echo "Waiting for Ollama service to become available..."
until curl -s http://127.0.0.1:${OLLAMA_PORT}/api/tags >/dev/null 2>&1; do
    sleep 1
done
echo "Ollama is ready."

# Launch your AI assistant agent
cd /app
echo "Starting AI assistant agent..."
exec python3 -u -m agents.ai_assistant_agent "$@"
