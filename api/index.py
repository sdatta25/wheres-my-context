"""Vercel serverless entrypoint.

Vercel's @vercel/python runtime serves the exported ASGI `app`. We just re-export
the FastAPI app from the backend package (repo root added to the path so the
`backend` package imports cleanly inside the function bundle).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.main import app  # noqa: E402,F401
