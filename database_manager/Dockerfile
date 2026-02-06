# Use a slim python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    # This prevents hnswlib from trying to use CPU-specific optimizations 
    # that might fail during cross-platform docker builds
    HNSWLIB_NO_NATIVE=1

# Create the application and database directory
WORKDIR /app
RUN mkdir -p /app/chroma_db

# Install system dependencies needed to build ChromaDB dependencies (hnswlib/duckdb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools && \
    pip install --no-cache-dir chromadb

# Expose ChromaDB's default port
EXPOSE 8000

# Start the chroma server
# --host 0.0.0.0 is mandatory to allow external connections to the container
# --path specifies where the data is persisted
CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8000", "--path", "/app/chroma_db"]
