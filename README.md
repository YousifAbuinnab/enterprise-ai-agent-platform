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

## RAG question answering

`POST /rag/ask` retrieves relevant document chunks and asks the configured LLM
to answer only from that context.

Request:
```json
{
   "question": "What is the refund policy?",
   "top_k": 5
}
```

`top_k` is optional and defaults to `5`. The response contains the generated
answer, unique source document names, and the retrieved chunk ids with their
similarity scores:
```json
{
   "answer": "Refunds are available within 30 days.",
   "sources": ["policy.txt"],
   "chunks": [
      {
         "chunk_id": 1,
         "document_id": 1,
         "filename": "policy.txt",
         "similarity_score": 0.9
      }
   ]
}
```

Configure the LLM in your local `.env`; never commit its API key:
```bash
LLM_PROVIDER=openai
LLM_API_KEY=your-real-api-key
LLM_MODEL=gpt-4o-mini
```

The application can start without `LLM_API_KEY`; the key is required only when
`POST /rag/ask` reaches the configured LLM provider.

## Project structure

```
app/
├── main.py           # FastAPI app instance and routes
└── core/
    └── config.py     # Settings loaded from environment variables / .env
```
