from fastapi import FastAPI

app = FastAPI(
    title="My First FastAPI App",
    version="1.0.0",
)

@app.get("/ai_assistant")
def read_root():
    return {"message": "Hello, FastAPI for AI Assistant is running!"}

@app.get("/ai_assistant/health")
def health_check():
    return {"status": "Running smoothly!"}
