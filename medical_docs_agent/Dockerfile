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
  poppler-utils \
  libgl1-mesa-glx \
  libglib2.0-0 \
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
COPY medical_docs_agent/requirements.txt /app/requirements.txt
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

# ------------------------
# App files
# ------------------------
RUN mkdir -p /app/medical_docs_agent/modules/configs

COPY medical_docs_agent/modules/configs/document_classes.yaml /app/medical_docs_agent/modules/configs/document_classes.yaml
COPY medical_docs_agent/modules/configs/folder_manager_state.yaml /app/medical_docs_agent/modules/configs/folder_manager_state.yaml
COPY medical_docs_agent/modules/medical_docs_ocr.py /app/medical_docs_agent/modules/medical_docs_ocr.py
COPY medical_docs_agent/modules/report_generator.py /app/medical_docs_agent/modules/report_generator.py
COPY medical_docs_agent/modules/__init__.py /app/medical_docs_agent/modules/__init__.py
COPY medical_docs_agent/schemas.py /app/medical_docs_agent/schemas.py
COPY medical_docs_agent/medical_docs_agent.py /app/medical_docs_agent/medical_docs_agent.py
COPY medical_docs_agent/medical_docs_agent_interface.py /app/medical_docs_agent/medical_docs_agent_interface.py
COPY medical_docs_agent/medical_docs_agent_folder_management.py /app/medical_docs_agent/medical_docs_agent_folder_management.py
COPY medical_docs_agent/start_medical_docs_docker.sh /app/medical_docs_agent/start_medical_docs_docker.sh

RUN chmod +x \
  /app/medical_docs_agent/modules/medical_docs_ocr.py \
  /app/medical_docs_agent/modules/report_generator.py \
  /app/medical_docs_agent/modules/__init__.py \
  /app/medical_docs_agent/schemas.py \
  /app/medical_docs_agent/medical_docs_agent.py \
  /app/medical_docs_agent/medical_docs_agent_interface.py \
  /app/medical_docs_agent/medical_docs_agent_folder_management.py \
  /app/medical_docs_agent/start_medical_docs_docker.sh

# ------------------------
# Runtime
# ------------------------
EXPOSE 11434
ENTRYPOINT ["/app/medical_docs_agent/start_medical_docs_docker.sh"]