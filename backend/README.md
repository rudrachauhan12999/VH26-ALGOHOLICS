# Backend — RAG-Based Intelligent Machine Troubleshooting System

FastAPI backend for the technician troubleshooting assistant. It owns
`backend/` only and talks to the RAG + AI layer through a single boundary:
`app/services/rag_service.py`. Right now that service is a mock so the
backend runs, tests, and demos on its own before RAG integration.

## Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn app.main:app --reload
```

- API base: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Test

```bash
pytest
```

Covers: health, successful troubleshooting (both machines), ambiguous
error code, insufficient information, invalid request, machines list,
manuals list.

## Example requests

```bash
# Health check
curl http://localhost:8000/health

# Success — machine specified
curl -X POST http://localhost:8000/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"query": "E101", "machine": "Machine A", "model": "X200"}'

# Ambiguous — no machine given, code exists on multiple machines
curl -X POST http://localhost:8000/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"query": "E101"}'

# Insufficient — unknown symptom
curl -X POST http://localhost:8000/api/troubleshoot \
  -H "Content-Type: application/json" \
  -d '{"query": "it is making a weird noise"}'

# Machines list
curl http://localhost:8000/api/machines

# Manuals list
curl http://localhost:8000/api/manuals

# Upload a manual (validation only — parsing happens in the RAG layer)
curl -X POST http://localhost:8000/api/upload \
  -F "file=@/path/to/Machine_A_Manual.pdf"
```

## Replacing mock RAG with the real pipeline

Everything the backend knows about RAG lives in one file:
`app/services/rag_service.py`. When the RAG teammate's `rag/pipeline.py`
is ready, replace the body of `troubleshoot()` with:

```python
from rag.pipeline import troubleshoot as real_troubleshoot

def troubleshoot(query, machine=None, model=None, conversation_id=None):
    return real_troubleshoot(
        query=query,
        machine=machine,
        model=model,
        conversation_id=conversation_id,
    )
```

No changes are needed to routes, schemas, or the frontend contract —
every route only ever calls `rag_service.troubleshoot(...)` and returns
whatever comes back. The `DEMO_MACHINES` / `DEMO_MANUALS` lists in the
same file can also be swapped for real data pulled from the RAG layer's
manual index once that exists.

## Folder structure

```
backend/
├── app/
│   ├── main.py                # FastAPI app, CORS, error handlers, /health
│   ├── routes/
│   │   ├── troubleshoot.py    # POST /api/troubleshoot
│   │   ├── machines.py        # GET /api/machines
│   │   └── manuals.py         # GET /api/manuals, POST /api/upload
│   ├── models/schemas.py      # Request/response Pydantic models
│   ├── services/rag_service.py  # Mock RAG boundary — swap point
│   └── config.py              # FRONTEND_URL from environment
├── tests/test_api.py
├── requirements.txt
├── .env.example
└── README.md
```
