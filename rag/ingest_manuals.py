"""
ingest_manuals.py

Entry point that builds the FAISS vector store from every manual listed in
the manifest (`demo/manuals_manifest.json` by default, configurable via the
RAG_MANUALS_MANIFEST env var). This only needs to be re-run when manuals
change - the index is persisted to disk and loaded instantly by
`rag.pipeline.troubleshoot()` afterwards.

Usage:
    python -m rag.ingest_manuals
"""

import json
import sys
from pathlib import Path

from rag.config import BASE_DIR, MANUALS_MANIFEST
from rag.ingestion.pdf_loader import load_pdf
from rag.chunking.chunker import chunk_records
from rag.embeddings.embedder import embed_texts
from rag.vectorstore.vector_store import VectorStore


def _resolve_manifest_path(entry_path: str) -> Path:
    p = Path(entry_path)
    if p.is_absolute():
        return p
    return (BASE_DIR / p).resolve()


def main():
    if not MANUALS_MANIFEST.exists():
        print(f"Manifest not found: {MANUALS_MANIFEST}", file=sys.stderr)
        sys.exit(1)

    with open(MANUALS_MANIFEST, "r", encoding="utf-8") as f:
        manifest_entries = json.load(f)

    if not manifest_entries:
        print("Manifest is empty - nothing to ingest.", file=sys.stderr)
        sys.exit(1)

    all_records = []
    for entry in manifest_entries:
        resolved_path = _resolve_manifest_path(entry["path"])
        print(f"Loading {resolved_path} ({entry['machine']} / {entry['model']})...")
        records = load_pdf(
            path=str(resolved_path),
            machine=entry["machine"],
            model=entry["model"],
            manual_name=entry.get("manual"),
        )
        print(f"  -> {len(records)} page(s) extracted")
        all_records.extend(records)

    print(f"Total pages extracted: {len(all_records)}")

    chunks = chunk_records(all_records)
    print(f"Total chunks produced: {len(chunks)}")

    texts = [c.text for c in chunks]
    print("Computing embeddings (local sentence-transformers model)...")
    vectors = embed_texts(texts)

    store = VectorStore()
    store.build(chunks, vectors)
    store.save()

    print(f"Vector store persisted. Indexed {len(chunks)} chunks from "
          f"{len(manifest_entries)} manual(s).")
    print(f"Known error codes: {sorted(store.error_code_map.keys())}")


if __name__ == "__main__":
    main()
