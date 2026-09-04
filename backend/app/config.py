"""
Application configuration.

Loads settings from environment variables (via a local .env file during
development). Only the frontend origin is required by the backend — the
RAG layer owns its own configuration (e.g. GROQ_API_KEY) separately.
"""

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")


settings = Settings()
