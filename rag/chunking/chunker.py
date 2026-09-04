"""
chunking/chunker.py

Turns extracted PageRecords into retrieval-ready Chunk objects.

Strategy (in priority order):
  1. Never merge text across a page boundary - a chunk always belongs to
     exactly one page, so page citations are always exact.
  2. Within a page, split on section headings first (a page can contain the
     tail of one section and the start of another).
  3. Within a section-on-a-page, split on paragraph breaks, and only fall
     back to a hard character-based split with overlap if a single
     paragraph is still larger than the target chunk size (e.g. a long
     troubleshooting procedure written as one block).
  4. A small character overlap is kept between consecutive chunks *within
     the same page/section* so that procedures split across a boundary
     aren't losing context at the seam.
"""

from typing import List

from rag.config import CHUNK_TARGET_CHARS, CHUNK_OVERLAP_CHARS
from rag.ingestion.pdf_loader import PageRecord, guess_section_for_page
from rag.schemas import Chunk, ChunkMetadata

import re

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


def _split_into_paragraphs(text: str) -> List[str]:
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
    if paragraphs:
        return paragraphs
    # No blank-line paragraphs found (common in PDF text extraction) - fall
    # back to line-based grouping.
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines or [text.strip()]


def _hard_split_with_overlap(text: str, target: int, overlap: int) -> List[str]:
    if len(text) <= target:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        end = min(start + target, len(text))
        # Try not to cut mid-word.
        if end < len(text):
            last_space = text.rfind(" ", start, end)
            if last_space > start:
                end = last_space
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [p for p in pieces if p]


def _group_paragraphs_into_chunks(
    paragraphs: List[str], target: int, overlap: int
) -> List[str]:
    """Greedily pack paragraphs into chunks close to `target` chars, and
    hard-split any paragraph that alone exceeds the target."""
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    def flush():
        if current:
            chunks.append("\n\n".join(current).strip())

    for para in paragraphs:
        if len(para) > target:
            # Flush what we have, then hard-split this oversized paragraph
            # on its own so we don't break a troubleshooting procedure
            # arbitrarily in the middle of unrelated text.
            flush()
            current, current_len = [], 0
            chunks.extend(_hard_split_with_overlap(para, target, overlap))
            continue

        if current_len + len(para) + 2 > target and current:
            flush()
            # keep a small tail of the previous chunk as overlap context
            tail = current[-1][-overlap:] if overlap else ""
            current = [tail] if tail else []
            current_len = len(tail)

        current.append(para)
        current_len += len(para) + 2

    flush()
    return [c for c in chunks if c]


def chunk_page(record: PageRecord, previous_section: str) -> (List[Chunk], str):
    """Chunk a single page's text, returning the chunks and the section name
    the page ended on (so the caller can carry it into the next page)."""
    section = guess_section_for_page(record.text, previous_section)
    paragraphs = _split_into_paragraphs(record.text)
    pieces = _group_paragraphs_into_chunks(
        paragraphs, CHUNK_TARGET_CHARS, CHUNK_OVERLAP_CHARS
    )

    chunks = [
        Chunk(
            text=piece,
            metadata=ChunkMetadata(
                manual=record.manual,
                machine=record.machine,
                model=record.model,
                section=section,
                page=record.page,
            ),
        )
        for piece in pieces
    ]
    return chunks, section


def chunk_records(records: List[PageRecord]) -> List[Chunk]:
    """Chunk a full list of PageRecords (e.g. an entire manual, or several
    manuals concatenated). Section context is carried per-manual."""
    all_chunks: List[Chunk] = []
    section_by_manual = {}

    for record in records:
        previous_section = section_by_manual.get(record.manual, "General")
        chunks, ending_section = chunk_page(record, previous_section)
        section_by_manual[record.manual] = ending_section
        all_chunks.extend(chunks)

    return all_chunks
