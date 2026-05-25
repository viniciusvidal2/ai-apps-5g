#!/bin/bash
set -e

# Ensure local Ollama setup (self-contained inside container)
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

# Launch the medical docs folder management agent
echo "Starting Medical Docs Folder Management Agent..."
cd /app/medical_docs_agent
exec python3 -u medical_docs_agent_folder_management.py "$@"
