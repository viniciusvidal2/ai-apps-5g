# AI Assistant Server

FastAPI server for AI Assistant integration, providing a REST API for frontend communication.

## Features

- **Inference**: Executes queries using AI Assistant with RAG
- **History**: Manages conversation history
- **Health Check**: Monitors server and AI Assistant status
- **CORS**: Configured for frontend communication

## Endpoints

### GET /
- **Description**: Root endpoint to verify if the server is working
- **Response**: Server status

### GET /health
- **Description**: Complete health check of server and AI Assistant
- **Response**: System health status

### POST /inference
- **Description**: Executes inference using AI Assistant
- **Body**:
  ```json
  {
    "query": "Your question here",
    "search_db": true,
    "use_history": true
  }
  ```
- **Response**:
  ```json
  {
    "answer": "AI Assistant response",
    "history_sources": [{"source": "document.pdf", "page": 1}]
  }
  ```

### POST /clear-history
- **Description**: Clears message history
- **Response**: Clear confirmation

### GET /history
- **Description**: Returns current message history
- **Response**: History and sources used

## Configuration

The server is configured through environment variables:

- `EMBEDDING_MODEL`: Embedding model (default: qwen3-embedding:0.6b)
- `INFERENCE_MODEL`: Inference model (default: gpt-oss:120b)
- `PERSIST_PATH`: Path to persist ChromaDB data
- `COLLECTION_NAME`: Collection name in ChromaDB

## Execution

### Local
```bash
pip install -r requirements.txt
python main.py
```

The server will be available at `http://localhost:8000`