# !/usr/bin/env python3
# This file should be used in docker build time to download necessary models
# for the AI Assistant agent to function properly.

from sentence_transformers import SentenceTransformer


print("Downloading embedding model at build time...")
SentenceTransformer(
    "Qwen/Qwen3-Embedding-0.6B",
    device="cpu"
)
print("Embedding model downloaded successfully.")
