"""Vercel serverless entrypoint — exposes the NEXUS FastAPI app."""
from nexus.server import app  # noqa: F401  (Vercel looks for `app`)
