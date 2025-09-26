# Chatbot AI

Intelligent chatbot with Next.js (frontend) and RAG integration using Python.

## Quick Start

```bash
# Complete setup
docker compose up --build -d

# Access: http://localhost:3000
```

## Structure

```
ihm/
├── client/                 # Next.js Frontend
├── docker-compose.yml     # Docker Services
└── README-SETUP.md        # Complete Documentation
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| **Frontend** | 3000 | Next.js App |
| **PostgreSQL** | 5433 | Database (Docker) |
| **Redis** | 6380 | Cache (Docker) |
