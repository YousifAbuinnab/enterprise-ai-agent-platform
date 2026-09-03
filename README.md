# Enterprise AI Agent Platform

A portfolio backend project simulating an internal company AI assistant: it answers questions
from company documents with retrieval-augmented generation (RAG), runs a bounded tool-calling
agent over customer/document data, and exposes the same tools over the Model Context Protocol
(MCP) for use by external MCP-compatible clients. Built with FastAPI, PostgreSQL + pgvector,
Docker, pytest, and GitHub Actions CI.

This project is a working local/Docker demo intended to showcase AI/LLM backend engineering
practices. It is **not** deployed to the cloud and has no authentication or production monitoring
— see [Limitations & future improvements](#limitations--future-improvements).

## Features

- **Customer management** — CRUD API backed by PostgreSQL.
- **Document ingestion** — upload `.txt`/`.pdf` files, extract text, and store per-document status.
- **Chunking & embeddings** — documents are split into overlapping chunks and embedded with
  `sentence-transformers` (`all-MiniLM-L6-v2`, 384 dimensions).
- **Vector search** — chunk embeddings are stored and queried with `pgvector` (cosine similarity)
  directly in PostgreSQL.
- **RAG question answering** — retrieves the most relevant chunks and asks an LLM to answer
  strictly from that context, returning cited sources.
- **Tool-calling agent** — a bounded agentic loop lets an LLM call typed tools (document search,
  customer lookup) to answer questions it can't answer directly.
- **MCP tool server** — the same tools are exposed over MCP (`FastMCP`) so any MCP client (e.g. an
  IDE agent) can discover and call them, not just the in-app agent.
- **Automated tests & CI** — pytest suite with mocked LLM calls, run automatically on every push/PR
  via GitHub Actions.

## Architecture

```
┌──────────────┐     ┌────────────────────────────────────────────┐
│  HTTP client │────▶│               FastAPI app                  │
└──────────────┘     │  /customers  /documents  /search  /rag  /agent
                      └───────────────────┬────────────────────────┘
                                          │
                       ┌──────────────────┼───────────────────────┐
                       ▼                  ▼                       ▼
               app/crud (DB ops)   app/services            app/services/tools.py
                       │           (parser, chunker,        (shared business logic:
                       │            embeddings, rag,         document search,
                       │            llm_client, agent)       customer lookup)
                       ▼                                          │
              PostgreSQL + pgvector                               │
                       ▲                                          ▼
                       │                                  app/mcp/server.py
                       └──────────────────────────────────  (FastMCP tool server,
                                                              reuses app/services/tools.py)
```

The agent (in-app, via `/agent/run`) and the MCP server both call into the same
`app/services/tools.py` functions, so tool logic (and its tests) is written once and shared by
both entry points.

## Tech stack

- **Language/runtime**: Python 3.12
- **Web framework**: FastAPI + Uvicorn
- **Database**: PostgreSQL 16 with the `pgvector` extension for vector similarity search
- **ORM/migrations**: SQLAlchemy 2.x, Alembic
- **Document parsing**: `pypdf` for PDFs, plain text for `.txt`
- **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2`), CPU-only `torch`
- **LLM integration**: provider-configurable client (`app/services/llm_client.py`); OpenAI
  implemented, calls mocked in tests
- **Tool protocol**: `mcp` (FastMCP) for exposing tools over the Model Context Protocol
- **Containerization**: Docker + Docker Compose (app + Postgres/pgvector, with healthchecks)
- **Testing**: pytest, FastAPI `TestClient`/`httpx`
- **CI**: GitHub Actions

## How RAG works

1. A document is uploaded via `POST /documents/upload`, text is extracted, and the raw text plus
   status are stored.
2. The text is split into overlapping chunks (`app/services/text_chunker.py`) and each chunk is
   embedded (`app/services/embeddings.py`) and stored in `document_chunks` (a `pgvector` column).
3. `POST /rag/ask` embeds the incoming question, retrieves the most similar chunks from Postgres,
   builds a context-only prompt (`app/services/rag.py`), and asks the LLM to answer using only
   that context.
4. The response includes the generated answer, the distinct source filenames, and the retrieved
   chunk ids with similarity scores — so an answer can always be traced back to its source text.
5. If no sufficiently similar chunks are found, the endpoint returns a "no answer" response instead
   of letting the LLM guess.

## How the tool-calling agent works

`POST /agent/run` (`app/services/agent.py`) runs a bounded loop, capped at
`MAX_TOOL_ITERATIONS` (5) round trips:

1. The user's message is sent to the LLM along with a fixed set of tool definitions
   (`search_company_documents`, `get_customer_by_id`, `list_customers`).
2. If the LLM responds with tool calls, each call's arguments are validated against a Pydantic
   schema before execution — unknown tools or invalid/malformed arguments are rejected without
   ever reaching the database.
3. Tool results are appended back into the conversation and the loop continues until the LLM
   answers directly (no more tool calls) or the iteration limit is reached.
4. The final response includes the answer plus a full trace of every tool call made and its
   result, so the reasoning is auditable rather than a black box.

## MCP tools

`app/mcp/server.py` exposes a `FastMCP` server (`enterprise-ai-agent-platform`) with three tools,
backed by the same functions the in-app agent uses:

| Tool | Description |
|---|---|
| `search_documents` | Search uploaded company documents for semantically relevant chunks. |
| `get_customer_by_id` | Retrieve one customer by numeric ID. |
| `list_customers` | List all customers with their basic details. |

Each tool validates its arguments (e.g. `customer_id >= 1`) and raises an MCP `ToolError` on
invalid input or unknown tool names, instead of leaking internal exceptions. Run it directly with:
```bash
python -m app.mcp.server
```

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

Configure the LLM in your local `.env`; never commit its API key:
```bash
LLM_PROVIDER=openai
LLM_API_KEY=your-real-api-key
LLM_MODEL=gpt-4o-mini
```

The application can start without `LLM_API_KEY`; the key is only required when `/rag/ask` or
`/agent/run` actually reach the configured LLM provider.

## Docker

Run the full stack (FastAPI app + PostgreSQL with `pgvector`) with Docker Compose:
```bash
docker compose up -d --build
```
This builds the app image, starts Postgres with a healthcheck, waits for it to become healthy,
and then starts the app on `http://localhost:8000`. Data persists in a named Docker volume
(`postgres_data`) across restarts. Bring the stack down with:
```bash
docker compose down
```

## Testing & CI

Run the test suite locally with:
```bash
pip install -r requirements-dev.txt
pytest
```

LLM calls are mocked in tests, so no real API key or network access is needed. A handful of tests
that require a live PostgreSQL connection (e.g. pgvector similarity search) skip automatically
when the database isn't reachable, and run for real against `docker compose up -d db`.

A GitHub Actions workflow ([.github/workflows/ci.yml](.github/workflows/ci.yml)) runs the full
pytest suite on every push and pull request targeting `main`, using Python 3.12 on Ubuntu with
pip dependency caching. It requires no external services or secrets to pass.

## Example API endpoints

| Method & path | Purpose |
|---|---|
| `GET /health` | Liveness check. |
| `GET /health/db` | Verifies the app can query PostgreSQL. |
| `POST /customers` | Create a customer. |
| `GET /customers` / `GET /customers/{id}` | List / fetch customers. |
| `POST /documents/upload` | Upload and process a document (`.txt`/`.pdf`). |
| `GET /documents` / `GET /documents/{id}` | List / fetch document metadata. |
| `GET /documents/{id}/content` | Fetch a document's extracted text. |
| `POST /search` | Vector-similarity search over document chunks. |
| `POST /rag/ask` | Ask a question answered from retrieved document context. |
| `POST /agent/run` | Run the bounded tool-calling agent on a free-form message. |

`POST /rag/ask` example:
```json
{
   "question": "What is the refund policy?",
   "top_k": 5
}
```
Response:
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

## Limitations & future improvements

This project demonstrates backend AI/agent engineering patterns locally; it is not production
software. Notably:

- **No cloud deployment** — runs locally or via Docker Compose only.
- **No authentication/authorization** — all endpoints are open, with no users, API keys, or RBAC.
- **No monitoring/observability stack** — only basic logging and `/health`/`/health/db` checks;
  no metrics, tracing, or alerting.
- **Single LLM provider implemented** — OpenAI adapter only; `llm_client.py` is structured to add
  others.
- **No rate limiting or request quotas.**
- **CI runs tests only** — no automated deploy, image publishing, or linting gate yet.

Natural next steps: add cloud deployment (e.g. a managed container platform), request
authentication, structured metrics/tracing, and a CI/CD pipeline that builds and publishes the
Docker image.

## Project structure

```
app/
├── main.py             # FastAPI app instance and route registration
├── core/
│   └── config.py        # Settings loaded from environment variables / .env
├── api/routes/          # customers, documents, search, rag, agent endpoints
├── crud/                # database read/write operations per model
├── db/                  # SQLAlchemy engine/session setup
├── models/               # SQLAlchemy models (customer, document, document_chunk)
├── schemas/              # Pydantic request/response models
├── services/             # parsing, chunking, embeddings, RAG, LLM client, agent, tools
└── mcp/server.py         # FastMCP server exposing shared tools over MCP
```
