import sys
import time
import httpx

BASE_URL = "http://0.0.0.0:8001/ai_assistant"


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
    response = httpx.get(f"{BASE_URL}")
    assert response.status_code == 200
    print("Response:", response.json(), "\n")


def test_status():
    """Test the ai assistant status endpoint of the API."""
    print("Testing GET /status")
    response = httpx.get(f"{BASE_URL}/status")
    assert response.status_code == 200
    print("Response:", response.json(), "\n")


def main():
    """Main function to run the tests."""
    wait_for_api()
    test_root()
    test_status()
    print("All checks passed ✅")


if __name__ == "__main__":
    main()
