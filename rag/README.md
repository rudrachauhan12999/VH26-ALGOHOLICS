# RAG-Based Intelligent Machine Troubleshooting System — `rag/` module

This is the **RAG + AI** module of the hackathon project. It is fully
self-contained, independent of `backend/` and `frontend/`, and exposes a
single function the backend team will call:

```python
from rag.pipeline import troubleshoot

result = troubleshoot(query, machine=None, model=None, conversation_id=None)
```

## What's inside

```
rag/
├── ingestion/pdf_loader.py     # PyMuPDF extraction, page-preserving
├── chunking/chunker.py         # section/paragraph-aware chunking + overlap
├── embeddings/embedder.py      # local sentence-transformers embeddings
├── retrieval/retriever.py      # hybrid exact-code + semantic + filtering
├── vectorstore/vector_store.py # FAISS index, persisted to disk
├── generation/groq_service.py  # Groq calls, strict JSON + Pydantic validation
├── conversation/memory.py      # simple in-memory follow-up context
├── pipeline.py                 # orchestrates everything -> troubleshoot()
├── schemas.py                  # shared Pydantic models
├── config.py                   # every tunable value, loaded from .env
├── ingest_manuals.py           # entry point: build + persist the index
├── test_rag.py                 # runnable test suite (all 6 required cases)
├── demo/
│   ├── build_demo_data.py      # generates 2 demo PDF manuals
│   └── manuals_manifest.json   # manual -> machine/model registration
└── data/                       # persisted FAISS index + metadata (generated)
```

## Setup

```bash
pip install -r rag/requirements.txt
cp rag/.env.example rag/.env
# then edit rag/.env and set GROQ_API_KEY (and GROQ_MODEL if you want a
# different Groq chat model)
```

## 1. Generate demo manuals

Two PDF manuals are generated on the fly so the whole pipeline can be
demoed without needing real scanned manuals:

- **Machine A / Model X200** — `E101` = *Motor overheating*
- **Machine B / Model H500** — `E101` = *Hydraulic pressure low*

This is the deliberate cross-manual ambiguity case, plus natural-language
overheating content for Machine A, plus no content at all about "clicking
noises" (to exercise the insufficient-evidence path).

```bash
python -m rag.demo.build_demo_data
```

## 2. Ingest manuals -> build the FAISS index

```bash
python -m rag.ingest_manuals
```

This extracts text page-by-page (PyMuPDF), chunks it (section/paragraph
aware, page-bounded, with overlap), embeds every chunk locally
(sentence-transformers), and persists a FAISS index + metadata + an
error-code lookup map to `rag/data/`. Re-run this only when manuals
change — `troubleshoot()` loads the persisted index rather than rebuilding
it on every call.

## 3. Run the test suite

```bash
python rag/test_rag.py
```

This exercises all 6 required scenarios: exact code + machine/model,
same code on a different machine, bare ambiguous code, natural-language
question, unsupported query (insufficient), and a follow-up question using
conversation memory.

## Sample output (abridged)

```text
======================================================================
TEST 1: E101 on Machine A / X200
======================================================================
{
  "status": "success",
  "answer": {
    "error_code": "E101",
    "meaning": "Motor overheating - the motor temperature sensor detected a temperature above the safe operating threshold.",
    "causes": ["Blocked ventilation grilles", "Excessive motor load due to an over-tightened drive belt"],
    "corrective_actions": ["Stop the machine", "Check ventilation grilles and clear any blockage", "Inspect and adjust drive belt tension"],
    "warnings": ["Allow the motor to cool before inspection; the housing may be hot enough to cause burns."],
    "sources": [
      {"manual": "Machine_A_Manual.pdf", "machine": "Machine A", "model": "X200", "section": "Error Code Reference", "page": 3}
    ]
  }
}

======================================================================
TEST 3: bare E101, no machine/model
======================================================================
{
  "status": "ambiguous",
  "message": "This error code exists for multiple machines.",
  "options": [
    {"machine": "Machine A", "model": "X200"},
    {"machine": "Machine B", "model": "H500"}
  ]
}

======================================================================
TEST 5: unsupported query
======================================================================
{
  "status": "insufficient",
  "message": "No sufficient information was found in the available manuals.",
  "sources": []
}
```

(Exact wording of `meaning`/`causes`/etc. comes from Groq and may vary
slightly between runs; `sources` are always exact, since they are taken
directly from retrieval metadata — never from the model.)

## How hallucination is controlled

Groq is **only** called after a real sufficiency check passes:

```
QUERY ANALYSIS -> RETRIEVAL -> RELEVANCE CHECK -> MACHINE/MODEL
CONSISTENCY CHECK -> SUFFICIENCY CHECK -> (only if sufficient) GROQ
```

- Exact error-code queries require an exact code match in the retrieved
  text — not just a high embedding score.
- Free-text queries require both a minimum top semantic score
  (`RAG_MIN_TOP_SCORE_SEMANTIC`) and a minimum number of relevant chunks
  (`RAG_MIN_RELEVANT_CHUNKS`), all configurable in `.env`.
- Groq's system prompt forbids outside knowledge and instructs it to
  return `{"sufficient": false}` if its own supplied context isn't enough
  — that response is treated as `insufficient` too.
- **Citations are never taken from the model.** `sources` in a `success`
  response are always rebuilt directly from the metadata of the chunks
  that were actually retrieved and sent to Groq.

## Backend integration

The backend developer never needs to know about PDFs, chunking,
embeddings, FAISS, or Groq — just:

```python
from rag.pipeline import troubleshoot

result = troubleshoot(
    query="E101",
    machine=None,          # optional
    model=None,            # optional
    conversation_id=None,  # optional, pass a stable ID to enable follow-ups
)
```

`result` is always a JSON-serializable dict with `status` equal to exactly
one of `"success" | "ambiguous" | "insufficient" | "error"` — see
`schemas.py` for the exact shape of each. It can be returned directly from
an API endpoint, e.g.:

```python
# example only - lives in backend/, not part of this module
@app.post("/troubleshoot")
def troubleshoot_endpoint(payload: TroubleshootRequest):
    return troubleshoot(
        query=payload.query,
        machine=payload.machine,
        model=payload.model,
        conversation_id=payload.conversation_id,
    )
```

## Notes on design trade-offs (intentional, hackathon-appropriate)

- **Machine/model per manual is registered in a manifest**, not guessed
  from PDF text. Guessing wrong would silently corrupt every citation;
  an explicit manifest is simple, correct, and trivial to extend with a
  real manual.
- **Conversation memory is in-process** (a plain dict), not a database —
  sufficient for a hackathon demo and easy to swap out later without
  touching the rest of `rag/`.
- **All thresholds are configurable** via `.env` / `config.py`, never
  hardcoded inline, so the sufficiency behavior can be tuned without
  touching retrieval or pipeline code.
