"""
FastAPI server for AI Assistant integration
"""
import sys
import os
from pathlib import Path
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import asyncio
from dotenv import load_dotenv

# Load environment variables from config file
load_dotenv('config.env')

# Add project root directory to path for ai_assistant import
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

# Configuration: Enable/disable AI Assistant
USE_AI_ASSISTANT = os.getenv("USE_AI_ASSISTANT", "false").lower() == "true"

# Conditional import based on configuration
if USE_AI_ASSISTANT:
    from ai_apis.ai_assistant import AiAssistant
    print("🤖 AI Assistant enabled - importing AiAssistant class")
else:
    print("🎭 Mock mode enabled - AI Assistant disabled")

# Server configuration
app = FastAPI(
    title="AI Assistant API",
    description="API for AI Assistant integration",
    version="1.0.0"
)

# CORS configuration to allow frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global AI Assistant instance (only if enabled)
ai_assistant = None

# Pydantic models for data validation
class InferenceRequest(BaseModel):
    """Model for inference requests"""
    query: str
    search_db: bool = True
    use_history: bool = True

class InferenceResponse(BaseModel):
    """Model for inference responses"""
    answer: str
    history_sources: list

class HealthResponse(BaseModel):
    """Model for health check response"""
    status: str
    message: str

@app.on_event("startup")
async def startup_event():
    """Initializes the AI Assistant when the server starts (only if enabled)"""
    global ai_assistant
    
    if not USE_AI_ASSISTANT:
        print("\n" + "="*60)
        print("🎭 MOCK MODE - AI ASSISTANT DISABLED")
        print("="*60)
        print("✅ Server ready in mock mode")
        print("🌐 Mock responses will be returned")
        print("="*60 + "\n")
        return
    
    try:
        print("\n" + "="*60)
        print("🚀 SERVER STARTUP - INITIALIZING AI ASSISTANT")
        print("="*60)
        
        # AI Assistant configuration
        embedding_model_name = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:latest")
        inference_model_name = os.getenv("INFERENCE_MODEL", "gpt-oss:120b")
        persist_path = os.getenv("PERSIST_PATH", "./chroma_db")
        collection_name = os.getenv("COLLECTION_NAME", "dev_collection")
        
        print(f"📋 Configuration:")
        print(f"   - Embedding Model: {embedding_model_name}")
        print(f"   - Inference Model: {inference_model_name}")
        print(f"   - Persist Path: {persist_path}")
        print(f"   - Collection: {collection_name}")
        
        print(f"\n🔄 Creating AI Assistant instance...")
        
        # Initialize AI Assistant
        ai_assistant = AiAssistant(
            embedding_model_name=embedding_model_name,
            inference_model_name=inference_model_name,
            persist_path=persist_path,
            collection_name=collection_name
        )
        
        print(f"✅ AI Assistant instance created")
        
        # Configure chunking parameters
        print(f"⚙️ Configuring chunking parameters...")
        ai_assistant.set_chunking_parameters(chunk_size=5000, chunk_overlap=200)
        ai_assistant.set_chunks_to_retrieve(n_chunks=3)
        
        print(f"✅ Chunking configured: size=5000, overlap=200, chunks=3")
        print("="*60)
        print("🎉 AI ASSISTANT INITIALIZED SUCCESSFULLY!")
        print("🌐 Server ready to receive requests")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR DURING STARTUP")
        print(f"🔍 Error type: {type(e).__name__}")
        print(f"📝 Error message: {str(e)}")
        print(f"📍 Error location: startup_event")
        print("="*60 + "\n")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleans up resources when the server stops (only if AI Assistant was enabled)"""
    global ai_assistant
    
    if not USE_AI_ASSISTANT or not ai_assistant:
        print("\n" + "="*60)
        print("🎭 MOCK MODE SHUTDOWN - NO CLEANUP NEEDED")
        print("="*60)
        print("👋 Server shutdown completed")
        print("="*60 + "\n")
        return
        
    try:
        print("\n" + "="*60)
        print("🔄 SERVER SHUTDOWN - CLOSING AI ASSISTANT")
        print("="*60)
        print("🔄 Calling ai_assistant.close_assistant()...")
        ai_assistant.close_assistant()
        print("✅ AI Assistant closed successfully!")
        print("="*60)
        print("👋 SERVER SHUTDOWN COMPLETED")
        print("="*60 + "\n")
    except Exception as e:
        print(f"\n⚠️ ERROR DURING SHUTDOWN")
        print(f"🔍 Error type: {type(e).__name__}")
        print(f"📝 Error message: {str(e)}")
        print(f"📍 Error location: shutdown_event")
        print("="*60 + "\n")

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
        if ai_assistant:
            print("✅ Health check passed - AI Assistant is active")
            return HealthResponse(
                status="healthy",
                message="AI Assistant is active and ready"
            )
        else:
            print("⚠️ Health check warning - AI Assistant not initialized")
            return HealthResponse(
                status="warning",
                message="AI Assistant enabled but not initialized"
            )
    else:
        print("✅ Health check passed - Mock mode active")
        return HealthResponse(
            status="healthy",
            message="Server working in mock mode"
        )

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
        print(f"🤖 AI Assistant: {'ENABLED' if USE_AI_ASSISTANT else 'DISABLED (Mock)'}")
        print(f"⏰ Timestamp: {__import__('datetime').datetime.now()}")
        print("="*60)
        
        if USE_AI_ASSISTANT and ai_assistant:
            # Use real AI Assistant
            print("🤖 Using AI Assistant for inference...")
            
            # Call AI Assistant
            result = ai_assistant.run_inference_pipeline(
                user_query=request.query,
                search_db=request.search_db,
                use_history=request.use_history
            )

            print("SOURCES:")
            for doc in result.get("history_sources", []):
                print(
                    f"- {doc.get('source', 'Unknown')}, (Page {doc.get('page', 'N/A')})")
            print("-" * 80)
            
            # Convert AI response to SSE format
            message_id = "ai-" + str(__import__('uuid').uuid4())
            ai_response = result.get('answer', 'No response generated')
            
            async def generate_ai_sse():
                """Generator que produz eventos SSE do AI Assistant"""
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
