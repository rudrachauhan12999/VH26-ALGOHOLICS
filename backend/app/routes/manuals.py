"""GET /api/manuals and POST /api/upload."""

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services import rag_service

router = APIRouter()


@router.get("/manuals")
async def get_manuals():
    return rag_service.DEMO_MANUALS


@router.post("/upload")
async def upload_manual(file: UploadFile = File(...)):
    """
    Accepts a PDF manual upload and validates it. This endpoint does NOT
    parse the PDF — that belongs to the RAG ingestion layer. For now it
    confirms the file was received so the frontend has something to
    integrate against before RAG ingestion exists.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Invalid file type.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return {
        "status": "success",
        "message": f"File '{file.filename}' received successfully.",
        "filename": file.filename,
        "size_bytes": len(contents),
    }
