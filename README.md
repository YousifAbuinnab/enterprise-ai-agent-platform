# Enterprise AI Agent Platform

An internal company AI assistant platform (in progress). Built as a portfolio project demonstrating
production-style practices for AI/LLM engineering: RAG, tool-calling agents, FastAPI, PostgreSQL,
Docker, testing, CI/CD, and observability.

## Status

**Phase 1: project foundation** — minimal FastAPI backend with a health-check endpoint. No RAG,
database, or agent functionality yet.

## Tech stack (so far)

- Python 3.12 (managed via [`uv`](https://github.com/astral-sh/uv), independent of system Python)
- FastAPI + Uvicorn
- pydantic-settings for configuration management

## Local setup

1. Create the virtual environment (Python 3.12, isolated from system Python):
   ```bash
   uv venv --python 3.12
   source .venv/bin/activate
   ```
2. Install dependencies:
   ```bash
   uv pip install -r requirements.txt
   ```
3. Copy the example environment file and adjust values if needed:
   ```bash
   cp .env.example .env
   ```
4. Run the development server:
   ```bash
   uvicorn app.main:app --reload
   ```
5. Check the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

## Project structure

```
app/
├── main.py           # FastAPI app instance and routes
└── core/
    └── config.py     # Settings loaded from environment variables / .env
```
