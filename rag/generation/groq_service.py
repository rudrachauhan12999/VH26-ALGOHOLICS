"""
generation/groq_service.py

All interaction with Groq lives here. Groq is:
  - the ONLY LLM used (never for embeddings)
  - only ever called with a small, pre-filtered context (never a full manual)
  - only ever called after the sufficiency check has already passed

If the configured Groq model doesn't have native structured-output support,
we fall back to strict JSON prompting + Pydantic validation + safe parsing,
with a configurable retry if the first response is malformed.
"""

import json
import re
from typing import List, Optional

from pydantic import ValidationError

from rag.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
    GROQ_JSON_RETRIES,
)
from rag.schemas import RetrievedChunk, TroubleshootAnswer


SYSTEM_PROMPT = """You are a factory machine troubleshooting assistant.

You MUST follow these rules exactly:
1. Use ONLY the supplied manual context below. Do not use outside knowledge.
2. Never invent error meanings, causes, corrective actions, or safety warnings.
3. Never invent citations, manual names, sections, or page numbers.
4. Do not alter or embellish source information.
5. If the supplied context does not contain enough information to answer,
   respond with the insufficient-evidence JSON shape shown below instead of guessing.
6. Prefer exact evidence from the context over assumptions.

Respond with ONLY a single valid JSON object. No markdown fences, no preamble,
no explanation text outside the JSON.

If there IS enough evidence, respond with exactly this shape:
{
  "sufficient": true,
  "error_code": "<error code if applicable, else null>",
  "meaning": "<short meaning of the issue, grounded in the context>",
  "causes": ["<cause 1>", "..."],
  "corrective_actions": ["<action 1>", "..."],
  "warnings": ["<warning 1>", "..."]
}

If there is NOT enough evidence in the context, respond with exactly:
{
  "sufficient": false
}
"""


def _format_context(chunks: List[RetrievedChunk]) -> str:
    blocks = []
    for i, chunk in enumerate(chunks, start=1):
        meta = chunk.metadata
        blocks.append(
            f"[Context {i}] manual={meta.manual} | machine={meta.machine} | "
            f"model={meta.model} | section={meta.section} | page={meta.page}\n"
            f"{chunk.text}"
        )
    return "\n\n".join(blocks)


def _build_user_prompt(query: str, chunks: List[RetrievedChunk], error_code: Optional[str]) -> str:
    context_block = _format_context(chunks)
    code_hint = f"\nDetected error code in the query: {error_code}" if error_code else ""
    return (
        f"Technician question: {query}{code_hint}\n\n"
        f"Manual context (the ONLY information you may use):\n"
        f"{context_block}\n\n"
        f"Respond with the JSON object described in the system prompt."
    )


def _extract_json_object(raw_text: str) -> Optional[dict]:
    """Safely pull a JSON object out of a model response, tolerating stray
    markdown fences or minor wrapping text."""
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to grabbing the first {...} block in the response.
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


class GroqGenerationError(Exception):
    """Raised when Groq cannot be reached or never returns usable JSON."""


def _call_groq(system_prompt: str, user_prompt: str):
    if not GROQ_API_KEY:
        raise GroqGenerationError("GROQ_API_KEY is not configured.")

    from groq import Groq  # imported lazily so the module is importable without the SDK installed

    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=GROQ_TEMPERATURE,
        max_tokens=GROQ_MAX_TOKENS,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content


def generate_answer(
    query: str,
    chunks: List[RetrievedChunk],
    error_code: Optional[str] = None,
) -> Optional[TroubleshootAnswer]:
    """Call Groq with a compact, pre-filtered context and return a validated
    TroubleshootAnswer, or None if the model reports insufficient evidence
    or repeatedly fails to return usable JSON.

    Sources are intentionally NOT populated here - the pipeline fills them
    in directly from the retrieved chunk metadata so citations can never be
    fabricated by the model.
    """
    if not chunks:
        return None

    user_prompt = _build_user_prompt(query, chunks, error_code)

    attempts = GROQ_JSON_RETRIES + 1
    last_error = None

    for attempt in range(attempts):
        system_prompt = SYSTEM_PROMPT
        if attempt > 0:
            system_prompt += (
                "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Respond again with ONLY the raw JSON object, nothing else."
            )

        try:
            raw_text = _call_groq(system_prompt, user_prompt)
        except Exception as exc:  # network / SDK errors
            last_error = exc
            continue

        parsed = _extract_json_object(raw_text or "")
        if parsed is None:
            last_error = ValueError(f"Model did not return valid JSON: {raw_text!r}")
            continue

        if parsed.get("sufficient") is False:
            return None

        try:
            answer = TroubleshootAnswer(
                error_code=parsed.get("error_code"),
                meaning=parsed["meaning"],
                causes=parsed.get("causes", []) or [],
                corrective_actions=parsed.get("corrective_actions", []) or [],
                warnings=parsed.get("warnings", []) or [],
                sources=[],  # filled in by the pipeline from retrieval metadata
            )
            return answer
        except (ValidationError, KeyError) as exc:
            last_error = exc
            continue

    raise GroqGenerationError(f"Groq failed to return usable JSON after {attempts} attempt(s): {last_error}")
