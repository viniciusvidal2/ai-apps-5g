import argparse
import os
from fastapi import FastAPI, BackgroundTasks, Request
from contextlib import asynccontextmanager
import uvicorn
from uuid import uuid4
import time
from modules.medical_docs_ocr import MedicalDocsOCR
from schemas import AppConfig, MedicalDocsInferenceRequest


def create_agent(config: AppConfig) -> FastAPI:
    """
    Creates and configures the FastAPI application for the Medical Docs Agent.

    Args:
        config (AppConfig): The configuration for the application.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """
        Defines the application lifespan context.
        """
        # --- startup ---
        print("Starting Medical Docs Agent...")
        # Store for tracking ongoing jobs
        app.state.job_store = {}
        # Initialize the OCR Agent and store it in the application state
        app.state.ocr_agent = MedicalDocsOCR(data_yaml_path=config.data_yaml_path)
        app.state.ocr_agent.set_output_folder(config.output_folder)
        print("Medical Docs Agent is ready!")

        yield

        # --- shutdown ---
        print("Shutting down Medical Docs Agent...")
        app.state.job_store.clear()

    app = FastAPI(
        title="Medical Docs Agent API",
        version="1.0.0",
        lifespan=lifespan
    )

    @app.get("/")
    def read_root() -> dict:
        """Returns a welcome message."""
        return {"message": "Hello, FastAPI for Medical Docs Agent is running!"}

    @app.get("/health")
    def health_check() -> dict:
        """Returns the health status of the API."""
        return {"status": "Running smoothly!"}

    @app.get("/ocr/status/{job_id}")
    def get_job_status(job_id: str) -> dict:
        """
        Returns the status and results of an OCR job.
        
        Args:
            job_id (str): The unique identifier for the job.
        """
        job_data = app.state.job_store.get(job_id)
        if not job_data:
            return {"error": "Job ID not found"}
        return job_data

    @app.post("/ocr/classify")
    def classify_docs(payload: MedicalDocsInferenceRequest, background_tasks: BackgroundTasks, request_obj: Request) -> dict:
        """
        Starts a background job to classify medical documents.

        Args:
            payload (MedicalDocsInferenceRequest): The input data containing document paths and options.
        """
        job_id = str(uuid4())
        app.state.job_store[job_id] = {
            "status": "running",
            "request_data": payload.model_dump()
        }
        
        # Add the OCR pipeline as a background task
        background_tasks.add_task(
            run_ocr_pipeline, 
            job_id=job_id, 
            payload=payload, 
            app=request_obj.app
        )
        
        return {"job_id": job_id, "status": "running"}

    def run_ocr_pipeline(job_id: str, payload: MedicalDocsInferenceRequest, app: FastAPI) -> None:
        """
        Executes the OCR, classification, and organization pipeline.
        """
        try:
            agent = app.state.ocr_agent
            
            # Ensure the agent is not already busy
            if agent.get_status() == "running":
                print(f"Job {job_id}: Agent is already busy. Waiting for previous job to finish...")
                while agent.get_status() == "running":
                    time.sleep(2)

            # Update agent settings based on payload
            if payload.ocr_method:
                agent.set_ocr_method(payload.ocr_method)
            if payload.classification_model:
                agent.set_classification_model(payload.classification_model)
            
            agent.set_documents_to_process(payload.document_paths)
            
            # Step 1: Start classification (now runs in its own internal thread)
            print(f"Job {job_id}: Starting classification worker...")
            agent.classify_documents()
            
            # Step 2: Poll agent status constantly
            while True:
                current_status = agent.get_status()
                app.state.job_store[job_id]["status"] = current_status
                
                if current_status == "completed":
                    print(f"Job {job_id}: Classification completed.")
                    results = agent.get_results()
                    
                    # Step 3: Organize documents in folders
                    print(f"Job {job_id}: Organizing documents...")
                    agent.organize_documents(results)
                    
                    # Update job store with final results
                    app.state.job_store[job_id].update({
                        "status": "completed",
                        "results": results
                    })
                    break
                elif current_status == "failed":
                    raise Exception("Classification worker failed internally.")
                
                # Keep polling
                time.sleep(1)
            
            print(f"Job {job_id}: Finished successfully.")
            
        except Exception as e:
            print(f"Job {job_id}: Failed with error: {str(e)}")
            app.state.job_store[job_id].update({
                "status": "failed",
                "error": str(e)
            })

    return app


def main():
    """Main function to run the API server."""
    parser = argparse.ArgumentParser(
        description="Run the Medical Docs Agent API server.")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--data_yaml_path", type=str, 
                        default=os.path.join(os.getenv("HOME", ""), "ai-apps-5g/medical_docs_agent/modules/data.yaml"))
    parser.add_argument("--output_folder", type=str, 
                        default=os.path.join(os.getenv("HOME", ""), "Desktop/5g_medical_docs/trials/classified_docs"))
    
    args = parser.parse_args()
    
    config = AppConfig(
        data_yaml_path=args.data_yaml_path,
        output_folder=args.output_folder,
        host=args.host,
        port=args.port
    )
    
    app = create_agent(config)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
