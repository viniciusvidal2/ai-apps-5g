"""
FastAPI server for AI Assistant integration
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from dotenv import load_dotenv
import subprocess
import json
import uuid
import threading
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion
from contextlib import asynccontextmanager

# Load environment variables from config file
load_dotenv('config.env')

# Add project root directory to path (for potential imports)
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configuration: Enable/disable AI Assistant (via MQTT/Docker)
USE_AI_ASSISTANT = os.getenv("USE_AI_ASSISTANT", "false").lower() == "true"

if USE_AI_ASSISTANT:
    print("🤖 AI Assistant enabled - using MQTT/Docker communication")
else:
    print("🎭 Mock mode enabled - AI Assistant disabled")

# Definir lifespan primeiro
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager para startup e shutdown"""
    global container_monitor_task
    
    # Startup
    if not USE_AI_ASSISTANT:
        print("\n" + "="*60)
        print("🎭 MOCK MODE - AI ASSISTANT DISABLED")
        print("="*60)
        print("✅ Server ready in mock mode")
        print("🌐 Mock responses will be returned")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("🚀 SERVER STARTUP - MQTT/DOCKER MODE")
        print("="*60)
        print("✅ Server ready - AI Assistant will be started via Docker")
        print("🌐 Communication via MQTT when container is started")
        print("="*60 + "\n")
        
        # Iniciar monitoramento do container
        container_monitor_task = asyncio.create_task(monitor_docker_container())
        print("🔍 Container monitor task iniciado")
    
    yield
    
    # Shutdown
    global mqtt_client_manager, docker_container_running
    
    print("\n" + "="*60)
    print("🔄 SERVER SHUTDOWN - CLEANING UP RESOURCES")
    print("="*60)
    
    # Cancelar task de monitoramento
    if container_monitor_task:
        try:
            print("🔄 Cancelando container monitor task...")
            container_monitor_task.cancel()
            try:
                await container_monitor_task
            except asyncio.CancelledError:
                pass
            print("✅ Container monitor task cancelado")
        except Exception as e:
            print(f"⚠️ Error canceling monitor task: {e}")
    
    # Disconnect MQTT client
    if mqtt_client_manager:
        try:
            print("🔄 Disconnecting MQTT client...")
            mqtt_client_manager.disconnect()
            print("✅ MQTT client disconnected")
        except Exception as e:
            print(f"⚠️ Error disconnecting MQTT client: {e}")
    
    # Stop Docker container
    if docker_container_running:
        try:
            print("🔄 Stopping Docker container...")
            stop_docker_container()
            print("✅ Docker container stopped")
        except Exception as e:
            print(f"⚠️ Error stopping Docker container: {e}")
    
    print("="*60)
    print("👋 SERVER SHUTDOWN COMPLETED")
    print("="*60 + "\n")

# Server configuration
app = FastAPI(
    title="AI Assistant API",
    description="API for AI Assistant integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Note: AI Assistant now runs in Docker container, communication via MQTT
# No local AiAssistant instance needed

# Session tracking: stores active sessions by session_id
# Format: {session_id: {"user_id": str, "timestamp": datetime}}
active_sessions: Dict[str, Dict[str, Any]] = {}

# Docker container state
docker_container_running = False
docker_container_name = "ai_assistant_agent"
container_monitor_task: Optional[asyncio.Task] = None

# MQTT Client Manager
mqtt_client_manager: Optional['MQTTClientManager'] = None


class MQTTClientManager:
    """Manages MQTT connection and communication with AI Assistant agent"""
    
    def __init__(self, broker: str, port: int, input_topic: str, output_topic: str):
        self.broker = broker
        self.port = port
        self.input_topic = input_topic
        self.output_topic = output_topic
        
        # Create MQTT client with V2 callback API
        self.client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        # Dictionary to track pending requests: {request_id: threading.Event}
        self.pending_requests: Dict[str, threading.Event] = {}
        # Dictionary to store responses: {request_id: response_data}
        self.responses: Dict[str, Dict[str, Any]] = {}
        
        # Thread-safe lock for pending_requests and responses
        self.lock = threading.Lock()
        
        # Connection state
        self.connected = False
        self.loop_started = False
        
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT client connects"""
        if rc == 0:
            print(f"✅ MQTT Client connected to broker {self.broker}:{self.port}")
            self.connected = True
            # Subscribe to output topic
            client.subscribe(self.output_topic, qos=2)
            print(f"📡 Subscribed to topic: {self.output_topic}")
        else:
            print(f"❌ MQTT Connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc, *args, **kwargs):
        """Callback when MQTT client disconnects"""
        # Handle both API versions - V2 has properties as 4th arg
        print(f"⚠️ MQTT Client disconnected (rc={rc})")
        self.connected = False
    
    def _on_message(self, client, userdata, msg):
        """Callback when message is received on subscribed topic"""
        try:
            payload = msg.payload.decode('utf-8')
            data = json.loads(payload)
            
            # Extract request_id if present (we'll add this to our requests)
            # For now, assume we only have one pending request at a time
            # or use a correlation mechanism
            
            # Try to find matching request_id in the message
            request_id = data.get("request_id")
            matched = False
            
            with self.lock:
                if request_id and request_id in self.pending_requests:
                    # Found matching request_id
                    matched = True
                elif self.pending_requests:
                    # No request_id, use the first pending request (FIFO)
                    # This handles agents that don't return request_id
                    request_id = list(self.pending_requests.keys())[0]
                    matched = True
                
                if matched:
                    # Store response
                    self.responses[request_id] = data
                    # Signal that response is ready
                    self.pending_requests[request_id].set()
                    print(f"✅ Received MQTT response for request {request_id}")
                else:
                    print(f"⚠️ Received MQTT message with no matching request: {data}")
                
        except Exception as e:
            print(f"❌ Error processing MQTT message: {e}")
    
    def connect(self):
        """Connect to MQTT broker"""
        try:
            print(f"🔄 Connecting to MQTT broker at {self.broker}:{self.port}...")
            self.client.connect(self.broker, self.port, keepalive=60)
            self.client.loop_start()
            self.loop_started = True
            # Wait a bit for connection to establish
            import time
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ Error connecting to MQTT broker: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from MQTT broker"""
        if self.loop_started:
            self.client.loop_stop()
        if self.connected:
            self.client.disconnect()
        self.connected = False
        self.loop_started = False
        print("🔌 MQTT Client disconnected")
    
    async def publish_and_wait(self, message: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
        """Publish message and wait for response"""
        if not self.connected:
            raise HTTPException(status_code=503, detail="MQTT broker not connected")
        
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        message["request_id"] = request_id
        
        # Create threading event to wait for response
        event = threading.Event()
        with self.lock:
            self.pending_requests[request_id] = event
            self.responses[request_id] = None
        
        try:
            # Publish message
            message_json = json.dumps(message)
            print(f"📤 Attempting to publish MQTT message to {self.input_topic}")
            print(f"   Message: {message_json[:200]}...")
            print(f"   Client connected: {self.connected}")
            print(f"   Client loop started: {self.loop_started}")
            
            result = self.client.publish(self.input_topic, message_json, qos=2)
            result.wait_for_publish(timeout=2)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                print(f"❌ Failed to publish MQTT message. Return code: {result.rc}")
                raise HTTPException(status_code=500, detail=f"Failed to publish MQTT message: return code {result.rc}")
            
            print(f"✅ MQTT message published successfully to {self.input_topic}")
            
            # Wait for response with timeout using asyncio executor
            loop = asyncio.get_event_loop()
            try:
                await asyncio.wait_for(
                    loop.run_in_executor(None, event.wait),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                raise HTTPException(status_code=504, detail=f"MQTT response timeout after {timeout}s")
            
            # Get response
            with self.lock:
                response = self.responses.get(request_id)
                if not response:
                    raise HTTPException(status_code=500, detail="No response received from MQTT")
                
                return response
                
        finally:
            # Cleanup
            with self.lock:
                self.pending_requests.pop(request_id, None)
                self.responses.pop(request_id, None)

# Helper functions for Docker management
def check_docker_container_status() -> Tuple[bool, Optional[str]]:
    """
    Verifica o status atual do container Docker
    Returns: (is_running: bool, container_id: Optional[str])
    """
    global docker_container_name
    try:
        # Verificar se está rodando
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.ID}}|{{.Names}}|{{.Status}}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if docker_container_name in result.stdout:
            # Container está rodando
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if docker_container_name in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        container_id = parts[0]
                        status = parts[2]
                        return True, container_id
            return True, None
        
        # Verificar se existe mas está parado
        result_stopped = subprocess.run(
            ["docker", "ps", "-a", "--filter", f"name={docker_container_name}", "--format", "{{.ID}}|{{.Names}}|{{.Status}}"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if docker_container_name in result_stopped.stdout:
            lines = result_stopped.stdout.strip().split('\n')
            for line in lines:
                if docker_container_name in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        container_id = parts[0]
                        status = parts[2]
                        return False, container_id
            return False, None
        
        return False, None
    except Exception as e:
        print(f"⚠️ Erro ao verificar status do container: {e}")
        return False, None


async def monitor_docker_container():
    """
    Task de background que monitora o container Docker periodicamente
    e detecta quando ele para inesperadamente
    """
    global docker_container_running, docker_container_name
    
    print("\n" + "="*80)
    print("🔍 MONITOR_DOCKER_CONTAINER - INICIADO")
    print("="*80)
    print("   - Monitoramento a cada 5 segundos")
    print("="*80 + "\n")
    
    consecutive_failures = 0
    last_status = None
    
    while True:
        try:
            await asyncio.sleep(5)  # Verificar a cada 5 segundos
            
            # Só monitorar se deveria estar rodando
            if docker_container_running:
                is_running, container_id = check_docker_container_status()
                
                if not is_running:
                    consecutive_failures += 1
                    print(f"\n⚠️ MONITOR: Container parou! (falha #{consecutive_failures})")
                    print(f"   - docker_container_running (flag): {docker_container_running}")
                    print(f"   - Container realmente rodando: {is_running}")
                    print(f"   - Container ID: {container_id}")
                    
                    if container_id:
                        # Tentar obter logs e informações do container
                        print(f"\n📋 Obtendo informações do container parado...")
                        
                        # Logs completos
                        result_logs = subprocess.run(
                            ["docker", "logs", container_id, "2>&1"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result_logs.stdout:
                            print(f"   - Últimos logs (últimos 1000 chars):\n{result_logs.stdout[-1000:]}")
                        if result_logs.stderr:
                            print(f"   - Erros (últimos 1000 chars):\n{result_logs.stderr[-1000:]}")
                        
                        # Exit code
                        result_inspect = subprocess.run(
                            ["docker", "inspect", container_id, "--format", "{{.State.ExitCode}}|{{.State.Error}}|{{.State.FinishedAt}}"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result_inspect.stdout:
                            parts = result_inspect.stdout.strip().split('|')
                            if len(parts) >= 3:
                                exit_code = parts[0]
                                error_msg = parts[1]
                                finished_at = parts[2]
                                print(f"   - Exit code: {exit_code}")
                                print(f"   - Error: {error_msg}")
                                print(f"   - Finished at: {finished_at}")
                        
                        # Status completo
                        result_status = subprocess.run(
                            ["docker", "inspect", container_id, "--format", "{{json .State}}"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result_status.stdout:
                            try:
                                state = json.loads(result_status.stdout)
                                print(f"   - Status completo: {json.dumps(state, indent=2)}")
                            except:
                                print(f"   - Status (raw): {result_status.stdout}")
                    
                    # Atualizar flag global
                    docker_container_running = False
                    print(f"   - docker_container_running atualizado para: {docker_container_running}")
                    
                    # Se falhou múltiplas vezes, parar de monitorar
                    if consecutive_failures >= 3:
                        print(f"\n❌ Container falhou {consecutive_failures} vezes consecutivas. Parando monitoramento.")
                        break
                else:
                    if consecutive_failures > 0:
                        print(f"✅ MONITOR: Container voltou a rodar (após {consecutive_failures} falhas)")
                    consecutive_failures = 0
                    last_status = "running"
            else:
                # Se não deveria estar rodando, resetar contador
                consecutive_failures = 0
                
        except asyncio.CancelledError:
            print("\n🛑 MONITOR_DOCKER_CONTAINER - CANCELADO")
            break
        except Exception as e:
            print(f"\n❌ Erro no monitoramento do container: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)  # Aguardar antes de tentar novamente


def start_docker_container(user_id: str = "1") -> bool:
    """Start the AI Assistant agent Docker container"""
    import traceback
    global docker_container_running, docker_container_name
    
    # Convert UUID string to integer hash for compatibility with agent
    # Agent expects integer user_id, but we receive UUID strings from frontend
    try:
        # Try to use as integer directly
        user_id_int = int(user_id)
    except ValueError:
        # If it's a UUID or other string, convert to hash integer
        user_id_int = abs(hash(user_id)) % (10 ** 8)
    
    print("\n" + "-"*80)
    print("🐳 START_DOCKER_CONTAINER - INÍCIO")
    print("-"*80)
    print(f"📥 Parâmetros recebidos:")
    print(f"   - user_id (original): {user_id}")
    print(f"   - user_id (converted to int): {user_id_int}")
    print(f"   - docker_container_name: {docker_container_name}")
    print(f"   - docker_container_running (antes): {docker_container_running}")
    
    # Check if container is already running
    print("\n🔍 Verificando se container já está rodando...")
    try:
        check_command = ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"]
        print(f"   - Comando: {' '.join(check_command)}")
        result = subprocess.run(
            check_command,
            capture_output=True,
            text=True,
            check=False
        )
        print(f"   - Return code: {result.returncode}")
        print(f"   - stdout: {result.stdout.strip()}")
        print(f"   - stderr: {result.stderr.strip()}")
        
        if docker_container_name in result.stdout:
            print(f"✅ Docker container {docker_container_name} is already running")
            docker_container_running = True
            print("-"*80 + "\n")
            return True
        else:
            print(f"ℹ️ Container não está rodando, verificando se existe mas parado...")
            # Container not running, check if it exists but stopped
            check_stopped_command = ["docker", "ps", "-a", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"]
            print(f"   - Comando: {' '.join(check_stopped_command)}")
            result_stopped = subprocess.run(
                check_stopped_command,
                capture_output=True,
                text=True,
                check=False
            )
            print(f"   - Return code: {result_stopped.returncode}")
            print(f"   - stdout: {result_stopped.stdout.strip()}")
            print(f"   - stderr: {result_stopped.stderr.strip()}")
            
            if docker_container_name in result_stopped.stdout:
                print(f"⚠️ Docker container {docker_container_name} exists but is not running")
                print(f"   - Removendo container parado...")
                # Try to remove it before starting a new one
                rm_result = subprocess.run(
                    ["docker", "rm", "-f", docker_container_name], 
                    capture_output=True, 
                    text=True,
                    check=False
                )
                print(f"   - rm return code: {rm_result.returncode}")
                print(f"   - rm stdout: {rm_result.stdout.strip()}")
                print(f"   - rm stderr: {rm_result.stderr.strip()}")
            else:
                print(f"ℹ️ Container não existe")
    except Exception as e:
        print(f"⚠️ Error checking Docker container status: {e}")
        print(f"   - Tipo do erro: {type(e).__name__}")
        print(f"   - Traceback:")
        traceback.print_exc()
    
    if docker_container_running:
        print(f"⚠️ Docker container {docker_container_name} is already running (cached state)")
        print("-"*80 + "\n")
        return True
    
    try:
        # Get configuration from environment
        print("\n📋 Lendo configuração do ambiente...")
        docker_image = os.getenv("DOCKER_IMAGE_NAME", "ai_assistant_image")
        mqtt_broker = os.getenv("MQTT_BROKER", "0.0.0.0")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        inference_model = os.getenv("INFERENCE_MODEL", "gemma3:4b")
        
        print(f"   - DOCKER_IMAGE_NAME: {docker_image}")
        print(f"   - MQTT_BROKER: {mqtt_broker}")
        print(f"   - MQTT_PORT: {mqtt_port}")
        print(f"   - INFERENCE_MODEL: {inference_model}")
        
        # Get absolute paths for ChromaDB databases
        # The databases should be in dbs/ (as expected by Dockerfile)
        documents_db_path = project_root / "dbs" / "chroma_documents_db"
        urls_db_path = project_root / "dbs" / "chroma_url_db"
        
        # Ensure directories exist (create empty if they don't)
        documents_db_path.mkdir(parents=True, exist_ok=True)
        urls_db_path.mkdir(parents=True, exist_ok=True)
        
        print(f"   - ChromaDB documents path: {documents_db_path}")
        print(f"   - ChromaDB URLs path: {urls_db_path}")
        
        # Build docker command with volume mounts for ChromaDB databases
        command = [
            "docker", "run", "-d", "--network=host",
            "--name", docker_container_name,
            # Mount ChromaDB databases from host to container
            # The code expects ./dbs/chroma_documents_db and ./dbs/chroma_url_db
            "-v", f"{documents_db_path}:/app/dbs/chroma_documents_db",
            "-v", f"{urls_db_path}:/app/dbs/chroma_url_db",
            docker_image,
            f"--broker={mqtt_broker}",
            f"--port={mqtt_port}",
            f"--user_id={user_id_int}",
            f"--input_topic=input",
            f"--output_topic=output",
            f"--inference_model_name={inference_model}"
        ]
        
        print(f"\n🔄 Starting Docker container...")
        print(f"   - Comando completo: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"   - Return code: {result.returncode}")
        print(f"   - stdout: {result.stdout.strip()}")
        print(f"   - stderr: {result.stderr.strip()}")
        
        container_id = result.stdout.strip()
        print(f"\n✅ Docker container {docker_container_name} started successfully")
        print(f"   - Container ID: {container_id}")
        
        # Wait a bit and verify container is still running
        print(f"\n⏳ Aguardando 3 segundos para container estabilizar...")
        import time
        time.sleep(3)
        print(f"   - Aguardamento concluído")
        
        print(f"\n🔍 Verificando se container ainda está rodando...")
        check_command = ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"]
        print(f"   - Comando: {' '.join(check_command)}")
        result_check = subprocess.run(
            check_command,
            capture_output=True,
            text=True,
            check=False
        )
        print(f"   - Return code: {result_check.returncode}")
        print(f"   - stdout: {result_check.stdout.strip()}")
        print(f"   - stderr: {result_check.stderr.strip()}")
        
        if docker_container_name in result_check.stdout:
            docker_container_running = True
            print(f"✅ Container verified running after startup")
            print(f"   - docker_container_running atualizado para: {docker_container_running}")
            
            # Check logs for any warnings/errors even if running
            print(f"\n📋 Verificando logs do container...")
            logs_command = ["docker", "logs", "--tail", "20", container_id]
            print(f"   - Comando: {' '.join(logs_command)}")
            result_logs = subprocess.run(
                logs_command,
                capture_output=True,
                text=True,
                check=False
            )
            print(f"   - Return code: {result_logs.returncode}")
            if result_logs.stdout:
                print(f"   - Recent container logs:\n{result_logs.stdout}")
            if result_logs.stderr:
                print(f"   - Container errors:\n{result_logs.stderr}")
            
            print("-"*80 + "\n")
            return True
        else:
            docker_container_running = False
            print(f"⚠️ Container started but stopped immediately. Checking logs...")
            print(f"   - docker_container_running atualizado para: {docker_container_running}")
            
            # Try to get logs from the container (might still exist even if stopped)
            print(f"\n📋 Tentando obter logs do container parado...")
            logs_command = ["docker", "logs", container_id, "2>&1"]
            print(f"   - Comando: {' '.join(logs_command)}")
            result_logs = subprocess.run(
                logs_command,
                capture_output=True,
                text=True,
                check=False
            )
            print(f"   - Return code: {result_logs.returncode}")
            if result_logs.stdout:
                print(f"   - Container logs (últimos 1000 chars):\n{result_logs.stdout[-1000:]}")
            if result_logs.stderr:
                print(f"   - Container errors (últimos 1000 chars):\n{result_logs.stderr[-1000:]}")
            
            # Also check exit code
            print(f"\n🔍 Verificando exit code do container...")
            inspect_command = ["docker", "inspect", container_id, "--format", "{{.State.ExitCode}}"]
            print(f"   - Comando: {' '.join(inspect_command)}")
            result_inspect = subprocess.run(
                inspect_command,
                capture_output=True,
                text=True,
                check=False
            )
            print(f"   - Return code: {result_inspect.returncode}")
            print(f"   - stdout: {result_inspect.stdout.strip()}")
            if result_inspect.stdout.strip():
                exit_code = result_inspect.stdout.strip()
                print(f"   - Container exit code: {exit_code}")
            
            print("-"*80 + "\n")
            return False
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to start Docker container (CalledProcessError)")
        print(f"   - Return code: {e.returncode}")
        print(f"   - Command: {e.cmd}")
        print(f"   - stdout: {e.stdout}")
        print(f"   - stderr: {e.stderr}")
        print(f"   - Traceback:")
        traceback.print_exc()
        docker_container_running = False
        print("-"*80 + "\n")
        return False
    except Exception as e:
        print(f"\n❌ Error starting Docker container")
        print(f"   - Tipo do erro: {type(e).__name__}")
        print(f"   - Mensagem: {str(e)}")
        print(f"   - Traceback:")
        traceback.print_exc()
        docker_container_running = False
        print("-"*80 + "\n")
        return False


def stop_docker_container() -> bool:
    """Stop the AI Assistant agent Docker container"""
    global docker_container_running, docker_container_name
    
    if not docker_container_running:
        print(f"⚠️ Docker container {docker_container_name} is not running")
        return True
    
    try:
        command = ["docker", "stop", docker_container_name]
        print(f"🔄 Stopping Docker container: {' '.join(command)}")
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        
        docker_container_running = False
        print(f"✅ Docker container {docker_container_name} stopped successfully")
        print(f"   Output: {result.stdout.strip()}")
        return True
        
    except subprocess.CalledProcessError as e:
        # Container might not exist, which is ok
        print(f"⚠️ Docker container stop result: {e.stderr}")
        docker_container_running = False
        return True  # Consider it successful if container doesn't exist
    except Exception as e:
        print(f"❌ Error stopping Docker container: {e}")
        return False


def initialize_mqtt_client() -> bool:
    """Initialize MQTT client manager"""
    import traceback
    global mqtt_client_manager
    
    print("\n" + "-"*80)
    print("📡 INITIALIZE_MQTT_CLIENT - INÍCIO")
    print("-"*80)
    
    if mqtt_client_manager:
        print("⚠️ MQTT client manager already initialized")
        print(f"   - mqtt_client_manager: {mqtt_client_manager}")
        print(f"   - mqtt_client_manager.connected: {mqtt_client_manager.connected}")
        print("-"*80 + "\n")
        return True
    
    try:
        print("📋 Lendo configuração do ambiente...")
        mqtt_broker = os.getenv("MQTT_BROKER", "0.0.0.0")
        mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
        input_topic = "input"
        output_topic = "output"
        
        print(f"   - MQTT_BROKER: {mqtt_broker}")
        print(f"   - MQTT_PORT: {mqtt_port}")
        print(f"   - input_topic: {input_topic}")
        print(f"   - output_topic: {output_topic}")
        
        print("\n🔧 Criando MQTTClientManager...")
        mqtt_client_manager = MQTTClientManager(
            broker=mqtt_broker,
            port=mqtt_port,
            input_topic=input_topic,
            output_topic=output_topic
        )
        print(f"✅ MQTTClientManager criado: {mqtt_client_manager}")
        
        print("\n🔌 Conectando ao broker MQTT...")
        mqtt_client_manager.connect()
        print(f"✅ Conexão estabelecida")
        print(f"   - mqtt_client_manager.connected: {mqtt_client_manager.connected}")
        print(f"   - mqtt_client_manager.loop_started: {mqtt_client_manager.loop_started}")
        print("-"*80 + "\n")
        return True
    except Exception as e:
        print(f"❌ Error initializing MQTT client: {e}")
        print(f"   - Tipo do erro: {type(e).__name__}")
        print(f"   - Traceback:")
        traceback.print_exc()
        print("-"*80 + "\n")
        return False


# Pydantic models for data validation
class InferenceRequest(BaseModel):
    """Model for inference requests"""
    query: str
    search_db: bool = True
    use_history: bool = True
    search_urls: bool = False
    n_chunks: int = 3

class InferenceResponse(BaseModel):
    """Model for inference responses"""
    answer: str
    history_sources: list

class HealthResponse(BaseModel):
    """Model for health check response"""
    status: str
    message: str

class ServiceRequest(BaseModel):
    """Model for service lifecycle requests"""
    session_id: str
    user_id: str

class ServiceResponse(BaseModel):
    """Model for service lifecycle responses"""
    status: str
    message: str
    active_sessions_count: int


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint to verify if the server is working"""
    print("📡 Root endpoint accessed")
    return HealthResponse(
        status="ok",
        message="AI Assistant API is working!"
    )

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    print("🏥 Health check requested")
    
    if USE_AI_ASSISTANT:
        # Check if Docker container is running and MQTT is connected
        global docker_container_running, mqtt_client_manager
        if docker_container_running and mqtt_client_manager and mqtt_client_manager.connected:
            print("✅ Health check passed - AI Assistant Docker container is running and MQTT connected")
            return HealthResponse(
                status="healthy",
                message="AI Assistant Docker container is running and MQTT connected"
            )
        else:
            print("⚠️ Health check warning - Docker container or MQTT not ready")
            return HealthResponse(
                status="warning",
                message="AI Assistant enabled but Docker container or MQTT not ready"
            )
    else:
        print("✅ Health check passed - Mock mode active")
        return HealthResponse(
            status="healthy",
            message="Server working in mock mode"
        )

@app.post("/turn_on_services", response_model=ServiceResponse)
async def turn_on_services(request: ServiceRequest):
    """
    Endpoint called when user enters the page
    Registers a new active session and starts Docker container if first session
    """
    from datetime import datetime
    import traceback
    
    print("\n" + "="*80)
    print("🟢 TURN_ON_SERVICES - INÍCIO")
    print("="*80)
    print(f"📥 Request recebido:")
    print(f"   - session_id: {request.session_id}")
    print(f"   - user_id: {request.user_id}")
    print(f"   - timestamp: {datetime.now()}")
    
    global docker_container_running, mqtt_client_manager
    
    try:
        # Log estado inicial das variáveis globais
        print(f"\n📊 Estado inicial das variáveis globais:")
        print(f"   - docker_container_running: {docker_container_running}")
        print(f"   - mqtt_client_manager: {mqtt_client_manager}")
        print(f"   - mqtt_client_manager.connected: {mqtt_client_manager.connected if mqtt_client_manager else 'N/A'}")
        print(f"   - active_sessions (antes): {len(active_sessions)}")
        print(f"   - active_sessions keys: {list(active_sessions.keys())}")
        
        # Register the session
        print(f"\n📝 Registrando nova sessão...")
        active_sessions[request.session_id] = {
            "user_id": request.user_id,
            "timestamp": datetime.now()
        }
        
        active_count = len(active_sessions)
        print(f"✅ Sessão registrada com sucesso")
        print(f"   - Sessões ativas: {active_count}")
        print(f"   - active_sessions keys (depois): {list(active_sessions.keys())}")
        
        # Start Docker container if this is the first active session
        print(f"\n🔍 Verificando se precisa iniciar Docker container...")
        print(f"   - active_count == 1: {active_count == 1}")
        print(f"   - not docker_container_running: {not docker_container_running}")
        print(f"   - Condição (active_count == 1 and not docker_container_running): {active_count == 1 and not docker_container_running}")
        
        if active_count == 1 and not docker_container_running:
            print("\n🚀 First active session detected - starting Docker container...")
            print(f"   - user_id para container: {request.user_id}")
            
            try:
                print(f"   - Chamando start_docker_container(user_id='{request.user_id}')...")
                docker_start_result = start_docker_container(user_id=request.user_id)
                print(f"   - Resultado de start_docker_container: {docker_start_result}")
                print(f"   - docker_container_running após start: {docker_container_running}")
                
                if docker_start_result:
                    print("✅ Docker container iniciado com sucesso")
                    print("   - Aguardando 2 segundos para container estabilizar...")
                    await asyncio.sleep(2)
                    print("   - Aguardamento concluído")
                    
                    # Verificar se container ainda está rodando após o sleep
                    print("   - Verificando se container ainda está rodando...")
                    try:
                        result_check = subprocess.run(
                            ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        container_still_running = docker_container_name in result_check.stdout
                        print(f"   - Container ainda rodando: {container_still_running}")
                        if not container_still_running:
                            print("   ⚠️ Container parou após iniciar! Verificando logs...")
                            # Tentar pegar logs do container mesmo que tenha parado
                            result_logs = subprocess.run(
                                ["docker", "logs", docker_container_name, "2>&1"],
                                capture_output=True,
                                text=True,
                                check=False
                            )
                            if result_logs.stdout:
                                print(f"   - Últimos logs do container:\n{result_logs.stdout[-500:]}")
                            if result_logs.stderr:
                                print(f"   - Erros do container:\n{result_logs.stderr[-500:]}")
                            docker_container_running = False
                    except Exception as check_error:
                        print(f"   ⚠️ Erro ao verificar container: {check_error}")
                    
                    # Initialize MQTT client
                    print("\n📡 Inicializando cliente MQTT...")
                    print(f"   - docker_container_running antes de initialize_mqtt: {docker_container_running}")
                    if docker_container_running:
                        try:
                            mqtt_init_result = initialize_mqtt_client()
                            print(f"   - Resultado de initialize_mqtt_client: {mqtt_init_result}")
                            print(f"   - mqtt_client_manager após init: {mqtt_client_manager}")
                            if mqtt_client_manager:
                                print(f"   - mqtt_client_manager.connected: {mqtt_client_manager.connected}")
                            
                            if not mqtt_init_result:
                                print("⚠️ Failed to initialize MQTT client, but container is running")
                            else:
                                print("✅ MQTT client inicializado com sucesso")
                        except Exception as mqtt_error:
                            print(f"❌ Erro ao inicializar MQTT client: {mqtt_error}")
                            print(f"   - Tipo do erro: {type(mqtt_error).__name__}")
                            print(f"   - Traceback:")
                            traceback.print_exc()
                    else:
                        print("⚠️ Container não está rodando, pulando inicialização MQTT")
                else:
                    print("⚠️ Failed to start Docker container")
                    print(f"   - docker_container_running após falha: {docker_container_running}")
            except Exception as docker_error:
                print(f"❌ Erro ao iniciar Docker container: {docker_error}")
                print(f"   - Tipo do erro: {type(docker_error).__name__}")
                print(f"   - Traceback:")
                traceback.print_exc()
        else:
            print("ℹ️ Não é necessário iniciar Docker container:")
            if active_count != 1:
                print(f"   - Motivo: active_count ({active_count}) != 1")
            if docker_container_running:
                print(f"   - Motivo: docker_container_running já é True")
        
        # If container is running but MQTT client not initialized, try to initialize it
        print(f"\n🔍 Verificando se precisa inicializar MQTT client...")
        print(f"   - docker_container_running: {docker_container_running}")
        print(f"   - not mqtt_client_manager: {not mqtt_client_manager}")
        print(f"   - Condição (docker_container_running and not mqtt_client_manager): {docker_container_running and not mqtt_client_manager}")
        
        if docker_container_running and not mqtt_client_manager:
            print("📡 Container rodando mas MQTT não inicializado - tentando inicializar...")
            try:
                mqtt_init_result = initialize_mqtt_client()
                print(f"   - Resultado de initialize_mqtt_client: {mqtt_init_result}")
                print(f"   - mqtt_client_manager após init: {mqtt_client_manager}")
                if mqtt_client_manager:
                    print(f"   - mqtt_client_manager.connected: {mqtt_client_manager.connected}")
                
                if not mqtt_init_result:
                    print("⚠️ Failed to initialize MQTT client")
                else:
                    print("✅ MQTT client inicializado com sucesso")
            except Exception as mqtt_error:
                print(f"❌ Erro ao inicializar MQTT client: {mqtt_error}")
                print(f"   - Tipo do erro: {type(mqtt_error).__name__}")
                print(f"   - Traceback:")
                traceback.print_exc()
        
        # Verificação final do container antes de retornar
        print(f"\n🔍 Verificação final do container...")
        if docker_container_running:
            is_running, container_id = check_docker_container_status()
            print(f"   - docker_container_running (flag): {docker_container_running}")
            print(f"   - Container realmente rodando: {is_running}")
            print(f"   - Container ID: {container_id}")
            
            if not is_running:
                print(f"   ⚠️ Container parou! Atualizando flag...")
                docker_container_running = False
                if container_id:
                    # Obter logs do container parado
                    result_logs = subprocess.run(
                        ["docker", "logs", container_id, "2>&1"],
                        capture_output=True,
                        text=True,
                        check=False
                    )
                    if result_logs.stdout:
                        print(f"   - Últimos logs do container:\n{result_logs.stdout[-1000:]}")
        
        # Log estado final
        print(f"\n📊 Estado final das variáveis globais:")
        print(f"   - docker_container_running: {docker_container_running}")
        print(f"   - mqtt_client_manager: {mqtt_client_manager}")
        print(f"   - mqtt_client_manager.connected: {mqtt_client_manager.connected if mqtt_client_manager else 'N/A'}")
        print(f"   - active_sessions: {active_count}")
        
        print(f"\n✅ TURN_ON_SERVICES - SUCESSO")
        print("="*80 + "\n")
        
        return ServiceResponse(
            status="ok",
            message="Services turned on",
            active_sessions_count=active_count
        )
        
    except Exception as e:
        print(f"\n❌ TURN_ON_SERVICES - ERRO CRÍTICO")
        print(f"   - Tipo do erro: {type(e).__name__}")
        print(f"   - Mensagem: {str(e)}")
        print(f"   - Traceback completo:")
        traceback.print_exc()
        print("="*80 + "\n")
        
        # Retornar resposta mesmo em caso de erro para não quebrar o frontend
        active_count = len(active_sessions)
        return ServiceResponse(
            status="error",
            message=f"Error turning on services: {str(e)}",
            active_sessions_count=active_count
        )

@app.post("/turn_off_services")
async def turn_off_services(request: Request):
    """
    Endpoint called when user leaves the page
    Removes the session and only turns off services if no other sessions are active
    Handles both JSON requests and sendBeacon blob requests
    """
    from datetime import datetime
    import json
    
    # Try to parse request body (handles both JSON and sendBeacon blob)
    session_id = ""
    user_id = ""
    
    try:
        # Read the raw body
        body = await request.body()
        if body:
            # Try to decode as JSON (handles both regular JSON and sendBeacon blob)
            try:
                data = json.loads(body.decode('utf-8'))
                session_id = data.get("session_id", "")
                user_id = data.get("user_id", "")
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                print(f"⚠️ Error decoding JSON from body: {e}")
                print(f"   Body content: {body[:100]}")  # Print first 100 chars for debugging
        else:
            print("⚠️ No data provided in request body")
            return {"status": "error", "message": "No data provided", "active_sessions_count": len(active_sessions)}
    except Exception as e:
        print(f"⚠️ Error parsing request: {e}")
        return {"status": "error", "message": f"Error parsing request: {str(e)}", "active_sessions_count": len(active_sessions)}
    
    if not session_id:
        print("⚠️ No session_id provided")
        return {"status": "error", "message": "No session_id provided", "active_sessions_count": len(active_sessions)}
    
    # Remove the session if it exists
    if session_id in active_sessions:
        removed_session = active_sessions.pop(session_id)
        print(f"🔴 Sessão removida - Session: {session_id}, User: {user_id}")
    else:
        print(f"⚠️ Tentativa de remover sessão inexistente - Session: {session_id}")
    
    active_count = len(active_sessions)
    
    # Only turn off services if there are no active sessions
    if active_count == 0:
        print(f"🔴 Função turn_off_services chamada - Nenhuma sessão ativa, serviços desligados")
        global docker_container_running, mqtt_client_manager
        
        # Disconnect MQTT client
        if mqtt_client_manager:
            try:
                mqtt_client_manager.disconnect()
                mqtt_client_manager = None
                print("🔌 MQTT client disconnected")
            except Exception as e:
                print(f"⚠️ Error disconnecting MQTT client: {e}")
        
        # Stop Docker container
        if docker_container_running:
            if stop_docker_container():
                print("🛑 Docker container stopped")
            else:
                print("⚠️ Failed to stop Docker container")
        
        return {
            "status": "ok",
            "message": "Services turned off - no active sessions",
            "active_sessions_count": 0
        }
    else:
        print(f"🟡 Sessão removida mas serviços permanecem ativos - Sessões ativas restantes: {active_count}")
        return {
            "status": "ok",
            "message": f"Session removed, services remain active - {active_count} active session(s)",
            "active_sessions_count": active_count
        }

@app.post("/inference")
async def run_inference(request: InferenceRequest):
    """
    Inference endpoint that returns SSE streaming response
    
    Args:
        request: Request data containing query, search_db and use_history
        
    Returns:
        SSE stream with AI response or mock response
    """
    try:
        print("\n" + "="*60)
        print("🚀 NEW INFERENCE REQUEST RECEIVED")
        print("="*60)
        print(f"📝 Query: {request.query}")
        print(f"🔍 Search DB: {request.search_db}")
        print(f"💬 Use History: {request.use_history}")
        print(f"🌐 Search URLs: {request.search_urls}")
        print(f"📊 N Chunks: {request.n_chunks}")
        print(f"🤖 AI Assistant: {'ENABLED' if USE_AI_ASSISTANT else 'DISABLED (Mock)'}")
        print(f"⏰ Timestamp: {__import__('datetime').datetime.now()}")
        print("="*60)
        
        if USE_AI_ASSISTANT:
            # Use MQTT to communicate with AI Assistant agent
            global docker_container_running, mqtt_client_manager
            
            # Verify container is actually running (not just cached state)
            try:
                result = subprocess.run(
                    ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                container_actually_running = docker_container_name in result.stdout
                if not container_actually_running:
                    docker_container_running = False
                    print(f"⚠️ Container {docker_container_name} is not actually running, attempting to restart...")
                    # Try to get user_id from active sessions
                    user_id = "1"
                    if active_sessions:
                        user_id = list(active_sessions.values())[0].get("user_id", "1")
                    if start_docker_container(user_id=user_id):
                        # Wait a bit for container to start and initialize
                        await asyncio.sleep(5)
                        # Re-check if container is running
                        result = subprocess.run(
                            ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if docker_container_name in result.stdout:
                            docker_container_running = True
                            print(f"✅ Container restarted and verified running")
                            # Wait a bit more for the agent to fully initialize
                            await asyncio.sleep(2)
                            # Re-initialize MQTT client if needed
                            if not mqtt_client_manager or not mqtt_client_manager.connected:
                                print("🔄 Re-initializing MQTT client after container restart...")
                                initialize_mqtt_client()
                        else:
                            docker_container_running = False
                            print(f"❌ Container restart failed - container not running")
                            raise HTTPException(
                                status_code=503,
                                detail="AI Assistant agent Docker container failed to start. Check server logs for details."
                            )
                    else:
                        docker_container_running = False
                        print(f"❌ Failed to restart container")
                        raise HTTPException(
                            status_code=503,
                            detail="AI Assistant agent Docker container failed to start. Check server logs for details."
                        )
                else:
                    # Container is running, update the flag
                    docker_container_running = True
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise
                print(f"⚠️ Error checking container status: {e}")
                docker_container_running = False
                raise HTTPException(
                    status_code=503,
                    detail="AI Assistant agent Docker container is not running. Please wait for services to start."
                )
            
            # Check if MQTT client is initialized and connected
            if not mqtt_client_manager:
                print("⚠️ MQTT client manager not initialized, attempting to initialize...")
                if not initialize_mqtt_client():
                    raise HTTPException(
                        status_code=503,
                        detail="MQTT client failed to initialize. Please wait for services to start."
                    )
            
            if not mqtt_client_manager.connected:
                print("⚠️ MQTT client not connected, attempting to reconnect...")
                try:
                    mqtt_client_manager.connect()
                except Exception as e:
                    print(f"❌ Failed to reconnect MQTT client: {e}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"MQTT client is not connected: {str(e)}"
                    )
            
            print("🤖 Using MQTT to communicate with AI Assistant agent...")
            
            # Final check: verify container is still running right before publishing
            result_final = subprocess.run(
                ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                check=False
            )
            if docker_container_name not in result_final.stdout:
                docker_container_running = False
                print(f"⚠️ Container stopped before publishing message. Attempting to restart...")
                # Try to restart one more time
                user_id = "1"
                if active_sessions:
                    user_id = list(active_sessions.values())[0].get("user_id", "1")
                if not start_docker_container(user_id=user_id):
                    raise HTTPException(
                        status_code=503,
                        detail="AI Assistant agent Docker container is not running and failed to restart."
                    )
                await asyncio.sleep(5)
                # Re-check
                result_final = subprocess.run(
                    ["docker", "ps", "--filter", f"name={docker_container_name}", "--format", "{{.Names}}"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                if docker_container_name not in result_final.stdout:
                    raise HTTPException(
                        status_code=503,
                        detail="AI Assistant agent Docker container failed to start. Please check server logs."
                    )
                docker_container_running = True
            
            # Prepare MQTT message
            mqtt_message = {
                "query": request.query,
                "search_db": request.search_db,
                "search_urls": request.search_urls,
                "use_history": request.use_history,
                "n_chunks": request.n_chunks
            }
            
            print(f"📋 Publishing message: {mqtt_message}")
            
            # Publish message and wait for response via MQTT
            try:
                result = await mqtt_client_manager.publish_and_wait(mqtt_message, timeout=600)
                
                # Extract response data
                ai_response = result.get("answer", "No response generated")
                document_sources = result.get("document_sources", [])
                url_sources = result.get("url_sources", [])
                
                print("SOURCES:")
                if document_sources:
                    for doc in document_sources:
                        print(f"- Document: {doc}")
                if url_sources:
                    for url in url_sources:
                        print(f"- URL: {url}")
                print("-" * 80)
                
                # Convert AI response to SSE format
                message_id = "ai-" + str(__import__('uuid').uuid4())
                
                async def generate_ai_sse():
                    """Generator que produz eventos SSE do AI Assistant via MQTT"""
                    import json
                    
                    # 1. Enviar start-step
                    yield f"data: {json.dumps({'type': 'start-step'})}\n\n"
                    
                    # 2. Enviar text-start
                    yield f"data: {json.dumps({'type': 'text-start', 'id': message_id})}\n\n"
                    
                    # 3. Enviar cada palavra como text-delta
                    words = ai_response.split()
                    for word in words:
                        yield f"data: {json.dumps({'type': 'text-delta', 'id': message_id, 'delta': word + ' '})}\n\n"
                        await asyncio.sleep(0.05)  # Faster streaming for AI
                    
                    # 4. Enviar text-end
                    yield f"data: {json.dumps({'type': 'text-end', 'id': message_id})}\n\n"
                    
                    # 5. Enviar finish-step
                    yield f"data: {json.dumps({'type': 'finish-step'})}\n\n"
                    
                    # 6. Enviar finish
                    yield f"data: {json.dumps({'type': 'finish'})}\n\n"
                    
                    # 7. Enviar [DONE]
                    yield "data: [DONE]\n\n"
                
                from fastapi.responses import StreamingResponse
                return StreamingResponse(
                    generate_ai_sse(),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive",
                        "X-Accel-Buffering": "no"
                    }
                )
                
            except HTTPException:
                # Re-raise HTTP exceptions (timeout, connection errors, etc.)
                raise
            except Exception as e:
                print(f"❌ Error in MQTT communication: {e}")
                raise HTTPException(status_code=500, detail=f"Error communicating with AI Assistant agent: {str(e)}")
            
        else:
            # Use mock response
            print("🎭 Using mock response...")
            
            # Mensagem de exemplo para streaming
            example_message = "Esta é uma resposta de exemplo do servidor"
            message_id = "mock-" + str(__import__('uuid').uuid4())
            
            async def generate_mock_sse():
                """Generator que produz eventos SSE compatíveis com AI SDK"""
                import json
                
                # 1. Enviar start-step
                yield f"data: {json.dumps({'type': 'start-step'})}\n\n"
                
                # 2. Enviar text-start
                yield f"data: {json.dumps({'type': 'text-start', 'id': message_id})}\n\n"
                
                # 3. Enviar cada palavra como text-delta
                words = example_message.split()
                for word in words:
                    yield f"data: {json.dumps({'type': 'text-delta', 'id': message_id, 'delta': word + ' '})}\n\n"
                    await asyncio.sleep(0.1)  # Simular delay de streaming
                
                # 4. Enviar text-end
                yield f"data: {json.dumps({'type': 'text-end', 'id': message_id})}\n\n"
                
                # 5. Enviar finish-step
                yield f"data: {json.dumps({'type': 'finish-step'})}\n\n"
                
                # 6. Enviar finish
                yield f"data: {json.dumps({'type': 'finish'})}\n\n"
                
                # 7. Enviar [DONE]
                yield "data: [DONE]\n\n"
            
            from fastapi.responses import StreamingResponse
            return StreamingResponse(
                generate_mock_sse(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
        
    except Exception as e:
        print(f"\n❌ ERROR DURING INFERENCE")
        print(f"🔍 Error type: {type(e).__name__}")
        print(f"📝 Error message: {str(e)}")
        print(f"📍 Error location: run_inference endpoint")
        print("="*60 + "\n")
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

# History endpoints removed - frontend manages its own history

if __name__ == "__main__":
    # Get configuration from environment variables
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True
    )
