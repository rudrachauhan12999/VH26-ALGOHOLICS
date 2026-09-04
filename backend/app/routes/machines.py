"""GET /api/machines — demo machine list for the frontend's dropdowns."""

from fastapi import APIRouter

from app.services import rag_service

router = APIRouter()


@router.get("/machines")
async def get_machines():
    return rag_service.DEMO_MACHINES
