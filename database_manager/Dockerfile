# Use a slim python image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HNSWLIB_NO_NATIVE=1

# Create the application and database directory
WORKDIR /app
RUN mkdir -p /app/chroma_db

# Install system dependencies needed to build ChromaDB dependencies (hnswlib/duckdb)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip setuptools
RUN pip install --no-cache-dir chromadb

# Start the chroma server
EXPOSE 8000
CMD ["chroma", "run", "--host", "0.0.0.0", "--port", "8000", "--path", "/app/chroma_db"]
