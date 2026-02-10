# Base image
FROM ubuntu:22.04

WORKDIR /app

# ------------------------
# System dependencies
# ------------------------
RUN apt-get update && apt-get install -y \
  ca-certificates \
  openssl \
  iputils-ping \
  && update-ca-certificates

RUN apt-get update && apt-get install -y \
  python3 \
  python3-distutils \
  python3-pip \
  curl \
  git \
  nano \
  zstd \
  && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

# ------------------------
# Install Ollama
# ------------------------
RUN curl -fsSL https://ollama.com/install.sh | sh

ENV OLLAMA_MODELS="/app/ollama_models"
ENV OLLAMA_HOST=http://127.0.0.1:11434
ENV OLLAMA_PORT=11434

RUN mkdir -p /app/ollama_models

# ------------------------
# Python deps
# ------------------------
RUN pip install --no-cache-dir setuptools==75.1.0
COPY ai_assistant/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --timeout=100 --retries=100 \
  -r /app/requirements.txt
ENV PYTHONUNBUFFERED=1

# ------------------------
# Build-time model selection
# ------------------------
ARG OLLAMA_MODELS_TO_PULL=""
RUN if [ -n "$OLLAMA_MODELS_TO_PULL" ]; then \
  echo "Checking Ollama manifests in filesystem" && \
  ollama serve > /var/log/ollama.log 2>&1 & \
  OLLAMA_PID=$! && \
  sleep 5 && \
  for model in $OLLAMA_MODELS_TO_PULL; do \
  NAME="${model%%:*}" ; \
  VERSION="${model##*:}" ; \
  MANIFEST="/app/ollama_models/manifests/registry.ollama.ai/library/${NAME}/${VERSION}" ; \
  if [ -f "$MANIFEST" ]; then \
  echo "✔ Manifest exists for $model — skipping pull" ; \
  else \
  echo "⬇ Pulling $model (manifest not found)" ; \
  ollama pull "$model" ; \
  fi ; \
  done && \
  kill $OLLAMA_PID ; \
  else \
  echo "No Ollama models requested at build time" ; \
  fi

# Huggingface embedding model cache
ENV HF_HOME=/opt/hf
RUN mkdir -p /opt/hf
COPY ai_assistant/modules/download_models.py /app/ai_assistant/modules/download_models.py
RUN python3 /app/ai_assistant/modules/download_models.py

# ------------------------
# App files
# ------------------------
RUN mkdir -p /app/ai_assistant/modules
COPY ai_assistant/modules/ai_assistant.py /app/ai_assistant/modules/ai_assistant.py
COPY ai_assistant/modules/web_content_extractor.py /app/ai_assistant/modules/web_content_extractor.py
COPY ai_assistant/modules/__init__.py /app/ai_assistant/modules/__init__.py
COPY ai_assistant/schemas.py /app/ai_assistant/schemas.py
COPY ai_assistant/ai_assistant_agent.py /app/ai_assistant/ai_assistant_agent.py
COPY ai_assistant/start_ai_assistant_docker.sh /app/ai_assistant/start_ai_assistant_docker.sh
RUN chmod +x \
  /app/ai_assistant/modules/ai_assistant.py \
  /app/ai_assistant/modules/web_content_extractor.py \
  /app/ai_assistant/modules/__init__.py \
  /app/ai_assistant/schemas.py \
  /app/ai_assistant/ai_assistant_agent.py \
  /app/ai_assistant/start_ai_assistant_docker.sh

# ------------------------
# Runtime
# ------------------------
EXPOSE 11434
EXPOSE 8001
ENTRYPOINT ["/app/ai_assistant/start_ai_assistant_docker.sh"]