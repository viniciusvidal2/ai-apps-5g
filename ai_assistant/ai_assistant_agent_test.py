import sys
import time
import httpx
import argparse
from schemas import AiAssistantInferenceRequest

BASE_URL = "http://0.0.0.0:8001"


def wait_for_api(timeout: int = 30) -> None:
    """
    Test if Agent API has become available

    Args:
        timeout (int, optional): Time to test the startup. Defaults to 30.
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


def test_status():
    """Test the ai assistant status endpoint of the API."""
    print("Testing GET /ai_assistant/status")
    response = httpx.get(f"{BASE_URL}/ai_assistant/status")
    assert response.status_code == 200
    print("Response:", response.json(), "\n")


def test_collections():
    """Test the ai assistant collections endpoint of the API."""
    print("Testing GET /ai_assistant/collections")
    response = httpx.get(f"{BASE_URL}/ai_assistant/collections")
    assert response.status_code == 200
    print("Response:", response.json(), "\n")


def test_inference(query: str = "What are the commitments of Santo Antonio Energia with the environment?",
                   collection: str = "my_collection",
                   n_chunks: int = 3) -> str:
    """
    Test the inference endpoint of the API.

    Args:
        query (str, optional): The query to test the inference endpoint with. Defaults to "What are the commitments of Santo Antonio Energia with the environment?".
        collection (str, optional): The collection name to use for inference. Defaults to "my_collection".
        n_chunks (int, optional): The number of chunks to use for inference. Defaults to 3.

    Returns:
        str: The job ID returned by the inference endpoint.
    """
    print("Testing POST /ai_assistant/inference")
    request_data = AiAssistantInferenceRequest(
        query=query,
        conversation_summary="",
        n_chunks=n_chunks,
        collection_name=collection,
        inference_model_name="gemma3:4b"
    )
    response = httpx.post(
        f"{BASE_URL}/ai_assistant/inference", json=request_data.model_dump())
    assert response.status_code == 200
    print("Response:", response.json(), "\n")
    return response.json().get("job_id")


def test_inference_result(job_id: str) -> None:
    """Test the inference result endpoint of the API."""
    print(f"Testing GET /ai_assistant/inference/{job_id}")
    # Wait for the inference job to complete
    status = ""
    while status != "completed":
        response = httpx.get(f"{BASE_URL}/ai_assistant/inference/{job_id}")
        assert response.status_code == 200
        response_data = response.json()
        print("Response:", response_data, "\n")
        status = response_data.get("status")
        response_message = response_data.get("response")
        status_message = response_data.get("status_message")
        if status == "completed":
            print("Inference job completed successfully!")
            print(f"Final status message: {status_message}")
            print("Inference response:", response_message, "\n")
            break
        elif status == "failed":
            print("Inference job failed with an error.")
            print(f"Error message: {response_message}")
            break
        else:
            print("Inference job is still processing, waiting...")
            print(f"Current status: {status}")
            time.sleep(2)


def main():
    """Main function to run the tests."""
    # Parse the input arguments for the base URL of the API
    global BASE_URL
    parser = argparse.ArgumentParser(
        description="Run AI Assistant Agent tests.")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8001",
                        help="Base URL of the AI Assistant API")
    parser.add_argument("--query", type=str, default="What are the commitments of Santo Antonio Energia with the environment?",
                        help="Query to test the inference endpoint")
    parser.add_argument("--collection", type=str, default="my_collection",
                        help="Collection name to use for inference")
    parser.add_argument("--n-chunks", type=int, default=3,
                        help="Number of chunks to use for inference")
    args = parser.parse_args()
    BASE_URL = args.base_url

    # Run the tests
    wait_for_api()
    test_root()
    test_status()
    test_collections()
    job_id = test_inference(
        query=args.query, collection=args.collection, n_chunks=args.n_chunks)
    test_inference_result(job_id)
    print("All tests passed ✅")


if __name__ == "__main__":
    main()
