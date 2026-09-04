"""
FastAPI application entrypoint.

Run with:  uvicorn app.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.routes import machines, manuals, troubleshoot

app = FastAPI(
    title="Machine Troubleshooting Backend",
    description="Backend API for the RAG-based machine troubleshooting assistant.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(troubleshoot.router, prefix="/api", tags=["troubleshoot"])
app.include_router(machines.router, prefix="/api", tags=["machines"])
app.include_router(manuals.router, prefix="/api", tags=["manuals"])


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Covers missing fields and invalid JSON bodies with the standard error shape."""
    return JSONResponse(
        status_code=400,
        content={
            "status": "error",
            "message": "Invalid request. Please check the required fields.",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Catch-all so no internal stack trace ever reaches the frontend."""
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Unable to process the troubleshooting request.",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
