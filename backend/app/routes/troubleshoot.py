"""POST /api/troubleshoot — the main technician-facing endpoint."""

from fastapi import APIRouter

from app.models.schemas import TroubleshootRequest
from app.services import rag_service

router = APIRouter()


@router.post("/troubleshoot")
async def troubleshoot(payload: TroubleshootRequest):
    """
    Passes the technician's query straight through to the RAG service
    and returns its response unchanged. Field names in both the request
    and the response are a fixed contract with the frontend — don't
    rename or reshape anything here.
    """
    try:
        result = rag_service.troubleshoot(
            query=payload.query,
            machine=payload.machine,
            model=payload.model,
            conversation_id=payload.conversation_id,
        )
        return result
    except Exception:
        # Never leak internal stack traces to the frontend.
        return {
            "status": "error",
            "message": "Unable to process the troubleshooting request.",
        }
