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
from dotenv import load_dotenv

# Load environment variables from config file
load_dotenv('config.env')

# Add project root directory to path for ai_assistant import
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from ai_apis.ai_assistant import AiAssistant

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

# Global AI Assistant instance
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
    """Initializes the AI Assistant when the server starts"""
    global ai_assistant
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
    """Cleans up resources when the server stops"""
    global ai_assistant
    if ai_assistant:
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
    global ai_assistant
    print("🏥 Health check requested")
    
    if ai_assistant is None:
        print("❌ Health check failed - AI Assistant not initialized")
        raise HTTPException(status_code=503, detail="AI Assistant not initialized")
    
    print("✅ Health check passed - AI Assistant is ready")
    return HealthResponse(
        status="healthy",
        message="Server and AI Assistant working correctly"
    )

@app.post("/inference", response_model=InferenceResponse)
async def run_inference(request: InferenceRequest):
    """
    Runs inference using the AI Assistant
    
    Args:
        request: Request data containing query, search_db and use_history
        
    Returns:
        Response with AI Assistant answer and sources used
    """
    global ai_assistant
    
    if ai_assistant is None:
        print("❌ AI Assistant not initialized")
        raise HTTPException(status_code=503, detail="AI Assistant not initialized")
    
    try:
        print("\n" + "="*60)
        print("🚀 NEW INFERENCE REQUEST RECEIVED")
        print("="*60)
        print(f"📝 Query: {request.query}")
        print(f"🔍 Search DB: {request.search_db}")
        print(f"💬 Use History: {request.use_history}")
        print(f"⏰ Timestamp: {__import__('datetime').datetime.now()}")
        print("="*60)
        
        print("\n🔄 CALLING AI ASSISTANT METHOD...")
        print(f"📞 Method: ai_assistant.run_inference_pipeline()")
        print(f"📋 Arguments:")
        print(f"   - user_query: '{request.query}'")
        print(f"   - search_db: {request.search_db}")
        print(f"   - use_history: {request.use_history}")
        
        # Execute inference pipeline
        response_data = ai_assistant.run_inference_pipeline(
            user_query=request.query,
            search_db=request.search_db,
            use_history=request.use_history
        )
        
        print(f"\n✅ AI ASSISTANT RESPONSE RECEIVED")
        print(f"📄 Answer length: {len(response_data['answer'])} characters")
        print(f"📚 Sources found: {len(response_data['history_sources'])}")
        print(f"📝 Answer preview: {response_data['answer'][:100]}...")
        
        if response_data['history_sources']:
            print(f"🔗 Sources used:")
            for i, source in enumerate(response_data['history_sources'][:3]):  # Show first 3 sources
                print(f"   {i+1}. {source.get('source', 'Unknown')} (Page {source.get('page', 'N/A')})")
        
        print("="*60)
        print("✅ INFERENCE COMPLETED SUCCESSFULLY")
        print("="*60 + "\n")
        
        return InferenceResponse(
            answer=response_data["answer"],
            history_sources=response_data["history_sources"]
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
