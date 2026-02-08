import sys
import time
import httpx
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


def test_inference():
    """Test the inference endpoint of the API."""
    print("Testing POST /ai_assistant/inference")
    request_data = AiAssistantInferenceRequest(
        query="Quais a companhias aéreas que operam no aeroporto de Guarulhos?",
        conversation_summary="",
        user_id="test_user",
        session_id="test_session",
        n_chunks=3,
        collection_name="none",
        inference_model_name="gemma3:4b"
    )
    response = httpx.post(
        f"{BASE_URL}/ai_assistant/inference", json=request_data.dict())
    assert response.status_code == 200
    print("Response:", response.json(), "\n")


def main():
    """Main function to run the tests."""
    wait_for_api()
    test_root()
    test_status()
    test_collections()
    test_inference()
    print("All checks passed ✅")


if __name__ == "__main__":
    main()
