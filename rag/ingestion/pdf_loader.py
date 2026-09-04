"""
ingestion/pdf_loader.py

Extracts text from PDF manuals using PyMuPDF (fitz), preserving page
numbers and attaching machine/model metadata supplied by the manifest.

Machine/model are NOT guessed from PDF content - a hackathon manual PDF
rarely states "this document is for Machine A, model X200" in a
machine-parseable way, and guessing wrong would silently corrupt every
citation downstream. Instead each manual is registered once in
`demo/manuals_manifest.json` with its machine/model, and that mapping is
trusted. Section headings, on the other hand, ARE detected from the text
itself (see `_guess_section`) since PDFs are internally consistent about
formatting even when the manifest doesn't know section names in advance.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import fitz  # PyMuPDF

_HEADING_PATTERNS = [
    # e.g. "4.2 Motor Troubleshooting", "Section 3: Hydraulics"
    re.compile(r"^\s*(?:\d+(?:\.\d+)*\s+)?([A-Z][A-Za-z0-9 /\-]{3,60})\s*$"),
]


@dataclass
class PageRecord:
    text: str
    page: int  # 1-indexed, human-friendly page number
    manual: str
    machine: str
    model: str


def _looks_like_heading(line: str) -> bool:
    line = line.strip()
    if not line or len(line) > 70:
        return False
    if line.endswith("."):
        return False
    # Mostly-capitalized or title-cased short lines are treated as headings.
    words = line.split()
    if not words:
        return False
    capitalized = sum(1 for w in words if w[:1].isupper())
    return capitalized / len(words) >= 0.6


def guess_section_for_page(page_text: str, previous_section: str) -> str:
    """Best-effort section-heading detection for a page of extracted text.

    Returns the last heading-like line found on the page, or falls back to
    the previous known section (sections often span multiple pages).
    """
    section = previous_section
    for raw_line in page_text.splitlines():
        line = raw_line.strip()
        if _looks_like_heading(line):
            for pattern in _HEADING_PATTERNS:
                match = pattern.match(line)
                if match:
                    section = match.group(1).strip()
                    break
            else:
                section = line
    return section


def load_pdf(
    path: str,
    machine: str,
    model: str,
    manual_name: Optional[str] = None,
) -> List[PageRecord]:
    """Extract every page of a PDF manual as a PageRecord.

    Page numbers are preserved exactly as they appear in the PDF (1-indexed)
    so that citations can always point back to a real, human-checkable page.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"Manual not found: {path}")

    manual_name = manual_name or pdf_path.name
    records: List[PageRecord] = []

    with fitz.open(str(pdf_path)) as doc:
        for page_index in range(len(doc)):
            page = doc[page_index]
            text = page.get_text("text") or ""
            text = text.strip()
            if not text:
                # Skip fully blank pages (e.g. cover separators) - nothing to
                # index and nothing worth citing.
                continue
            records.append(
                PageRecord(
                    text=text,
                    page=page_index + 1,
                    manual=manual_name,
                    machine=machine,
                    model=model,
                )
            )

    return records


def load_manuals_from_manifest(manifest_entries: List[dict]) -> List[PageRecord]:
    """Load every manual described in the manifest.

    Each manifest entry looks like:
        {"path": "demo/manuals/machine_a_x200.pdf",
         "machine": "Machine A", "model": "X200",
         "manual": "Machine_A_Manual.pdf"}   # manual name is optional
    """
    all_records: List[PageRecord] = []
    for entry in manifest_entries:
        records = load_pdf(
            path=entry["path"],
            machine=entry["machine"],
            model=entry["model"],
            manual_name=entry.get("manual"),
        )
        all_records.extend(records)
    return all_records
