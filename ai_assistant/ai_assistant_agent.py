import argparse
import time
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
import uvicorn
import json
from typing import Generator
from uuid import uuid4
from modules.ai_assistant import AiAssistant
from schemas import AppConfig, AiAssistantInferenceRequest
import threading
import queue


def create_agent(config: AppConfig) -> FastAPI:
    """
    Creates and configures the FastAPI application for the AI Assistant Agent.

    Args:
        config (AppConfig): The configuration for the application.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """

    # region Application setup and endpoints

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
        # Store for tracking ongoing jobs (inference requests)
        app.state.job_store = {}
        # Initialize the AI Assistant and store it in the application state
        app.state.ai_assistant = AiAssistant(
            inference_model_name=config.inference_model_name,
            db_ip_address=config.db_ip_address
        )
        print("Ai Assistant agent is ready!")

        yield

        # --- shutdown ---
        print("Shutting down application...")
        app.state.job_store.clear()
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

    # endregion
    # region AI Assistant gets

    @app.get("/ai_assistant/status")
    def get_status() -> dict:
        """
        Returns the current status of the AI assistant.

        Returns:
            dict: The current status of the AI assistant.
        """
        return {"status": app.state.ai_assistant.get_assistant_status()}

    @app.get("/ai_assistant/collections")
    def get_collections() -> dict:
        """
        Returns the list of collection names available in the database.

        Returns:
            dict: The list of collection names available in the database.
        """
        return app.state.ai_assistant.get_collections_state()

    @app.get("/ai_assistant/available_models")
    def get_available_models() -> dict:
        """
        Returns the list of available Ollama models.

        Returns:
            dict: The list of available Ollama models.
        """
        return {"available_models": app.state.ai_assistant.get_available_ollama_models()}

    @app.get("/ai_assistant/conversation_summary")
    def get_conversation_summary() -> dict:
        """
        Returns the current conversation summary for the user session.

        Returns:
            dict: The current conversation summary for the user session.
        """
        return {"conversation_summary": app.state.ai_assistant.get_assistant_conversation_summary()}

    @app.get("/ai_assistant/inference/{job_id}")
    def get_inference_result(job_id: str) -> dict:
        """
        Returns the result of an inference job based on the provided job ID.

        Args:
            job_id (str): The unique identifier for the inference job.

        Returns:
            dict: The result of the inference job, including the response and status.
        """
        job_data = app.state.job_store.get(job_id)
        if not job_data:
            return {"error": "Job ID not found"}
        return {"response": job_data.get("response"), "status_message": app.state.ai_assistant.get_assistant_status(), "status": job_data.get("status")}

    # endregion
    # region AI Assistant posts

    @app.post("/ai_assistant/inference")
    def run_inference(payload: AiAssistantInferenceRequest, background_tasks: BackgroundTasks, request_obj: Request) -> dict:
        """
        Runs the inference pipeline of the AI assistant based on the provided request data.

        Args:
            request (AiAssistantInferenceRequest): The input data for the inference request.

        Returns:
            dict: The response from the AI assistant after running the inference pipeline.
        """
        # Create a unique job ID for this inference request and store the request data in the job store
        job_id = str(uuid4())
        app.state.job_store[job_id] = {
            "request_data": payload.model_dump(),
            "status_message": app.state.ai_assistant.get_assistant_status(),
            "status": "running",
        }
        # Add inference background task to run the inference pipeline and return the job ID and current assistant status
        background_tasks.add_task(
            run_ai_assistant_inference, job_id=job_id, inferece_payload=payload, app=request_obj.app)
        return {"job_id": job_id, "status_message": app.state.ai_assistant.get_assistant_status(), "status": "running"}

    @app.post("/ai_assistant/inference/stream")
    def run_inference_stream(payload: AiAssistantInferenceRequest) -> StreamingResponse:
        """
        Runs the inference pipeline with streaming response. Yields response chunks in real-time.

        Args:
            payload (AiAssistantInferenceRequest): The input data for the inference request.

        Returns:
            StreamingResponse: Streamed response chunks as JSON lines.
        """
        def generate_stream() -> Generator[str, None, None]:
            """
            Generator that runs inference and yields response chunks as JSON strings.
            Uses a background thread to prevent connection drops while waiting for the LLM.
            """
            # Create a queue to communicate between the main thread and the worker thread
            q = queue.Queue()
            # Create and start the worker thread
            inference_thread = threading.Thread(target=inference_worker, kwargs={
                                      "inference_payload": payload, "queue": q})
            inference_thread.start()
            # List to store response chunks
            response_chunks = []
            while True:
                try:
                    # Wait up to 2 seconds for a chunk
                    msg = q.get(timeout=2.0)
                    assistant_status = app.state.ai_assistant.get_assistant_status()
                    # Check what to do based on the message type
                    if msg["type"] == "end":
                        status_data = {
                            "type": "status",
                            "status": msg.get("data", assistant_status),
                            "data": msg.get("data", assistant_status)
                        }
                        yield json.dumps(status_data) + "\n"
                        break
                    elif msg["type"] == "error":
                        error_data = {
                            "type": "error",
                            "error": msg["error"],
                            "status": "An error occurred during inference"
                        }
                        yield json.dumps(error_data) + "\n"
                        return
                    elif msg["type"] == "chunk":
                        response_chunks.append(msg["data"])
                        chunk_data = {
                            "type": "chunk",
                            "data": msg["data"],
                            "status": assistant_status
                        }
                        yield json.dumps(chunk_data) + "\n"
                    elif msg["type"] == "status":
                        status_data = {
                            "type": "status",
                            "status": msg.get("data", assistant_status),
                            "data": msg.get("data", assistant_status)
                        }
                        yield json.dumps(status_data) + "\n"
                    else:
                        yield json.dumps(msg) + "\n"
                except queue.Empty:
                    # Timeout waiting for queue, yield keep-alive status
                    keep_alive_data = {
                        "type": "status",
                        "status": app.state.ai_assistant.get_assistant_status()
                    }
                    yield json.dumps(keep_alive_data) + "\n"
            inference_thread.join()
            # Start thread to update conversation history summary without blocking the main thread
            full_response = "".join(response_chunks)
            history_thread = threading.Thread(target=history_update_worker, kwargs={
                "user_query": payload.query,
                "context_string": app.state.ai_assistant.get_context_string(),
                "assistant_response": full_response
            })
            history_thread.start()
            assistant_status = app.state.ai_assistant.get_assistant_status()
            while history_thread.is_alive():
                # While waiting for the history update to finish, we can yield keep-alive status updates
                keep_alive_data = {
                    "type": "status",
                    "status": assistant_status
                }
                yield json.dumps(keep_alive_data) + "\n"
                time.sleep(2)
            history_thread.join()
            # Send final status update
            final_data = {
                "type": "complete",
                "data": full_response,
                "status": app.state.ai_assistant.get_assistant_status()
            }
            yield json.dumps(final_data) + "\n"

        return StreamingResponse(
            generate_stream(),
            media_type="application/x-ndjson"
        )

    # endregion
    # region Background tasks

    def inference_worker(inference_payload: AiAssistantInferenceRequest, queue: queue.Queue) -> None:
        """
        Worker to deal with inference thread stream

        Args:
            inference_payload (AiAssistantInferenceRequest): user payload for the inference request
            queue (queue.Queue): Queue to put inference results into
        """
        try:
            # Treat the requested model and switch if it's different from the current one
            requested_model_name = inference_payload.inference_model_name
            if requested_model_name != app.state.ai_assistant.get_inference_model_name():
                app.state.ai_assistant.switch_assistant_model(
                    inference_model_name=requested_model_name)
            # Set the conversation history for the user session
            app.state.ai_assistant.set_assistant_conversation_summary(
                summary=inference_payload.conversation_summary
            )
            # Stream inference chunks
            for response_chunk in app.state.ai_assistant.run_inference_pipeline(
                    user_query=inference_payload.query,
                    collection_name=inference_payload.collection_name):
                if response_chunk == "[END_OF_RESPONSE]":
                    queue.put({"type": "end"})
                elif isinstance(response_chunk, dict):
                    queue.put(response_chunk)
                else:
                    queue.put({"type": "chunk", "data": response_chunk})
        except Exception as e:
            queue.put({"type": "error", "error": str(e)})

    def history_update_worker(user_query: str, context_string: str, assistant_response: str) -> None:
        """
        Worker to update the agent conversation history in a separate thread

        Args:
            user_query (str): The user's query that was sent for inference
            context_string (str): The context string that was used for the inference
            assistant_response (str): The response generated by the assistant for the given query and context
        """
        try:
            app.state.ai_assistant.update_conversation_history_summary(
                user_query=user_query,
                context_string=context_string,
                assistant_response=assistant_response,
            )
        except Exception as e:
            print(
                f"Error updating conversation history summary: {str(e)}")

    def run_ai_assistant_inference(job_id: str, inferece_payload: AiAssistantInferenceRequest, app: FastAPI) -> None:
        """
        Runs the inference pipeline for a given job ID and updates the job status in the job store.

        Args:
            job_id (str): The unique identifier for the inference job.
            inferece_payload (AiAssistantInferenceRequest): The input data for the inference request.
            app (FastAPI): The FastAPI application instance to access the job store and AI assistant
        """
        try:
            # Treat the requested model and switch if it's different from the current one
            requested_model_name = inferece_payload.inference_model_name
            if requested_model_name != app.state.ai_assistant.get_inference_model_name():
                app.state.ai_assistant.switch_assistant_model(
                    inference_model_name=requested_model_name)
            # Set the conversation history for the user session
            app.state.ai_assistant.set_assistant_conversation_summary(
                summary=inferece_payload.conversation_summary
            )
            response_chunks = []
            for response_chunk in app.state.ai_assistant.run_inference_pipeline(
                user_query=inferece_payload.query,
                collection_name=inferece_payload.collection_name,
            ):
                # Skip the end-of-response marker
                if response_chunk != "[END_OF_RESPONSE]":
                    response_chunks.append(response_chunk)

            response = "".join(response_chunks)
            app.state.ai_assistant.update_conversation_history_summary(
                user_query=inferece_payload.query,
                context_string=app.state.ai_assistant.get_context_string(),
                assistant_response=response,
            )
            app.state.job_store[job_id]["response"] = response
            app.state.job_store[job_id]["status_message"] = app.state.ai_assistant.get_assistant_status(
            )
            app.state.job_store[job_id]["status"] = "completed"
        except Exception as e:
            app.state.job_store[job_id]["response"] = str(e)
            app.state.job_store[job_id]["status_message"] = "An error occurred during inference"
            app.state.job_store[job_id]["status"] = "failed"

    # endregion

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
