import argparse
from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn
from modules.ai_assistant import AiAssistant
from schemas import AppConfig


def create_agent(config: AppConfig) -> FastAPI:
    """
    Creates and configures the FastAPI application for the AI Assistant Agent.

    Args:
        config (AppConfig): The configuration for the application.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
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
            inference_model_name=config.inference_model_name, db_ip_address=config.db_ip_address)
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

    @app.get("/")
    def read_root() -> dict:
        """
        Returns a welcome message indicating the API is running.

        Returns:
            dict: A welcome message indicating the API is running.
        """
        return {"message": "Hello, FastAPI for AI Assistant is running!"}

    @app.get("/health")
    def health_check() -> dict:
        """
        Returns the health status of the API.

        Returns:
            dict: The health status of the API.
        """
        return {"status": "Running smoothly!"}

    @app.get("/ai_assistant/status")
    def get_status() -> dict:
        """
        Returns the current status of the AI assistant.

        Returns:
            dict: The current status of the AI assistant.
        """
        return {"status": app.state.ai_assistant.get_assistant_status()}

    return app


def main():
    """Main function to run the API server."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Run the AI Assistant Agent API server.")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--db_ip_address", type=str, default="localhost")
    parser.add_argument("--inference_model_name",
                        type=str, default="gemma3:4b")
    args = parser.parse_args()
    # Create the application configuration and run the API server
    config = AppConfig(
        db_ip_address=args.db_ip_address,
        inference_model_name=args.inference_model_name,
        host=args.host,
        port=args.port
    )
    app = create_agent(config)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
