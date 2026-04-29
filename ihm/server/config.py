"""Configuration utilities for the FastAPI server."""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from config file in the same directory as this file
config_file = Path(__file__).parent / "config.env"
load_dotenv(config_file)
print(f"[config] Loading config from: {config_file}")
print(f"[config] Config file exists: {config_file.exists()}")

# Add project root directory to path (for potential imports)
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in os.sys.path:
    os.sys.path.append(str(project_root))

DEFAULT_HOST = os.getenv("HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("PORT", 8000))
INFERENCE_MODEL_NAME = os.getenv("INFERENCE_MODEL", "gemma4:latest")
USE_AI_ASSISTANT = os.getenv("USE_AI_ASSISTANT", "false").lower() == "true"
AI_ASSISTANT_API_URL = os.getenv("AI_ASSISTANT_API_URL", "http://localhost:8001")
AI_ASSISTANT_DB_IP_ADDRESS = os.getenv(
    "AI_ASSISTANT_DB_IP_ADDRESS",
    "host.docker.internal",
)
AI_ASSISTANT_CONTAINER_NAME = os.getenv(
    "AI_ASSISTANT_CONTAINER_NAME",
    "ai_assistant_global",
)
AI_ASSISTANT_HEALTH_TIMEOUT_SECONDS = int(
    os.getenv("AI_ASSISTANT_HEALTH_TIMEOUT_SECONDS", "180")
)
AI_ASSISTANT_POLL_INTERVAL_SECONDS = float(
    os.getenv("AI_ASSISTANT_POLL_INTERVAL_SECONDS", "2.0")
)
AI_ASSISTANT_INTERNAL_PORT = int(os.getenv("AI_ASSISTANT_INTERNAL_PORT", "8001"))
SESSION_IDLE_TTL_SECONDS = int(os.getenv("SESSION_IDLE_TTL_SECONDS", "600"))
SESSION_SWEEP_INTERVAL_SECONDS = float(
    os.getenv("SESSION_SWEEP_INTERVAL_SECONDS", "60")
)

print(f"[config] USE_AI_ASSISTANT env value: '{os.getenv('USE_AI_ASSISTANT', 'NOT_SET')}'")
print(f"[config] USE_AI_ASSISTANT parsed to: {USE_AI_ASSISTANT}")
AI_ASSISTANT_START_API_URL = os.getenv(
    "AI_ASSISTANT_START_API_URL",
    "http://localhost:8002/ai_assistant/start_docker",
)
AI_ASSISTANT_KILL_API_URL = os.getenv(
    "AI_ASSISTANT_KILL_API_URL",
    "http://localhost:8002/ai_assistant/kill_docker",
)

print(f"[config] AI_ASSISTANT_API_URL: {AI_ASSISTANT_API_URL}")
print(f"[config] AI_ASSISTANT_START_API_URL: {AI_ASSISTANT_START_API_URL}")
print(f"[config] AI_ASSISTANT_KILL_API_URL: {AI_ASSISTANT_KILL_API_URL}")
print(f"[config] AI_ASSISTANT_CONTAINER_NAME: {AI_ASSISTANT_CONTAINER_NAME}")
print(f"[config] INFERENCE_MODEL: {INFERENCE_MODEL_NAME}")
print(f"[config] SESSION_IDLE_TTL_SECONDS: {SESSION_IDLE_TTL_SECONDS}")
print(f"[config] SESSION_SWEEP_INTERVAL_SECONDS: {SESSION_SWEEP_INTERVAL_SECONDS}")
print("=" * 80)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
