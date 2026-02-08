from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from modules.ai_assistant import AiAssistant


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Defines the application context that will live throughout the execution in 
    all the endpoints.

    Args:
        app (FastAPI): The FastAPI application instance.
    """
    # --- startup ---
    print("Starting application...")
    app.state.ai_assistant = AiAssistant(
        inference_model_name="nemotron-3-nano:30b", db_ip_address="localhost")
    print("Ai Assistant agent is ready!")

    yield

    # --- shutdown ---
    print("Shutting down application...")
    app.state.ai_assistant.close_assistant()

app = FastAPI(
    title="The AI Assistant Agent API",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/ai_assistant")
def read_root():
    return {"message": "Hello, FastAPI for AI Assistant is running!"}


@app.get("/ai_assistant/health")
def health_check():
    return {"status": "Running smoothly!"}


@app.get("/ai_assistant/status")
def get_status():
    return {"status": app.state.ai_assistant.get_assistant_status()}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
