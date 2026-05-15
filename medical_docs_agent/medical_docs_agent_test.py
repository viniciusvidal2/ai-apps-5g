import sys
import time
import httpx
import argparse
import json
import os
from schemas import MedicalDocsInferenceRequest

BASE_URL = "http://0.0.0.0:8002"


def wait_for_api(timeout: int = 60) -> None:
    """
    Test if Medical Docs Agent API has become available.

    Args:
        timeout (int, optional): Time to test the startup. Defaults to 60.
    """
    print("Waiting for API to become available...")

    start = time.time()
    while time.time() - start < timeout:
        try:
            response = httpx.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                print("API is ready\n")
                return
            else:
                print(
                    f"API responded with status {response.status_code}, retrying...")
        except httpx.RequestError:
            pass

        time.sleep(1)

    print("ERROR: API did not start in time")
    sys.exit(1)


def test_root():
    """Test the root endpoint of the API."""
    print("Testing GET root endpoint")
    response = httpx.get(f"{BASE_URL}/")
    assert response.status_code == 200
    print("Response:", response.json(), "\n")


def test_classify(document_paths: list, ocr_method: str = "paddle", 
                  classification_model: str = "gemma4:e2b") -> str:
    """
    Test the document classification endpoint.

    Args:
        document_paths (list): List of paths to PDF documents.
        ocr_method (str): OCR method to use ("paddle" or "llm").
        classification_model (str): LLM model name for classification.

    Returns:
        str: The job ID.
    """
    print(f"Testing POST /ocr/classify with method: {ocr_method}")
    payload = MedicalDocsInferenceRequest(
        document_paths=document_paths,
        ocr_method=ocr_method,
        classification_model=classification_model
    )
    response = httpx.post(
        f"{BASE_URL}/ocr/classify", json=payload.model_dump())
    
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        print("Response:", response.text)
        sys.exit(1)
        
    job_id = response.json().get("job_id")
    print(f"Job started! ID: {job_id}\n")
    return job_id


def test_job_status(job_id: str) -> None:
    """
    Poll the status of an OCR job until completion or failure.

    Args:
        job_id (str): The unique identifier for the job.
    """
    print(f"Polling status for job ID: {job_id}")
    status = ""
    while status != "completed":
        response = httpx.get(f"{BASE_URL}/ocr/status/{job_id}")
        assert response.status_code == 200
        data = response.json()
        
        status = data.get("status")
        if status == "completed":
            print("\nJob completed successfully! ✅")
            print("Results Summary:")
            results = data.get("results", {})
            for doc_name, info in results.items():
                print(f"  - {doc_name}: {info.get('classification')}")
            break
        elif status == "failed":
            print("\nJob failed! ❌")
            print("Error message:", data.get("error"))
            break
        else:
            print(f"Current status: {status}...", end="\r", flush=True)
            time.sleep(2)
    print("\n")


def main():
    """Main function to run the tests."""
    global BASE_URL
    parser = argparse.ArgumentParser(
        description="Run Medical Docs Agent tests.")
    parser.add_argument("--base_url", type=str, default="http://127.0.0.1:8002",
                        help="Base URL of the Medical Docs API")
    parser.add_argument("--document_paths", type=str, nargs="+", 
                        default=["/home/vini/Desktop/5g_medical_docs/trials/20251127_103128_cardiologia.pdf"],
                        help="List of PDF paths to process")
    parser.add_argument("--ocr_method", type=str, default="paddle",
                        help="OCR method: 'paddle' or 'llm'")
    parser.add_argument("--model", type=str, default="gemma4:e2b",
                        help="Classification model name")
    
    args = parser.parse_args()
    BASE_URL = args.base_url

    # Run the tests
    wait_for_api()
    test_root()
    
    # Test with PaddleOCR
    job_id_paddle = test_classify(args.document_paths, ocr_method="paddle", classification_model=args.model)
    test_job_status(job_id_paddle)
    
    # Test with LLM OCR (Optional/Uncomment if needed)
    # job_id_llm = test_classify(args.document_paths, ocr_method="llm", classification_model=args.model)
    # test_job_status(job_id_llm)

    print("All tests passed! ✅")


if __name__ == "__main__":
    main()
