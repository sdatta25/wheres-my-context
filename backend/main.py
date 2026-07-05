"""
Where's My Context — FastAPI backend.

Serves the single-page frontend and a small JSON API over the pluggable
`MemoryEngine`. Run:  uvicorn backend.main:app --reload
"""
from __future__ import annotations

import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path = ROOT / ".env") -> None:
    """Tiny stdlib .env loader (no python-dotenv dep). Existing env wins."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from .memory import build_engine  # noqa: E402
from . import seed  # noqa: E402

FRONTEND = ROOT / "frontend"

app = FastAPI(title="Where's My Context", version="1.0.0")
engine = build_engine()


@app.exception_handler(Exception)
async def _clean_errors(request: Request, exc: Exception):
    """A judge should never see a raw stack trace — always return tidy JSON so
    the UI can degrade gracefully even if the memory backend misbehaves."""
    return JSONResponse(status_code=500, content={"error": str(exc)[:200] or "internal error"})


@app.middleware("http")
async def _no_cache(request, call_next):
    """Dev-friendly: never cache the static frontend so edits show on reload."""
    resp = await call_next(request)
    if not request.url.path.startswith("/api"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

# Load demo data on boot so the graph is never empty for a judge.
if os.getenv("SEED_ON_START", "1") == "1":
    seed.load_into(engine)


# --------------------------- request models -------------------------------- #

class AddReq(BaseModel):
    text: str
    type: str = "note"
    project: str = "default"
    author: str = ""


class SearchReq(BaseModel):
    query: str
    project: str | None = None


class RecallReq(BaseModel):
    project: str
    task: str = ""


# ------------------------------- API --------------------------------------- #

@app.get("/api/status")
def status():
    st = engine.status()
    st["projects"] = getattr(engine, "projects", lambda: [])()
    st["count"] = len(engine.list(None))
    return st


@app.get("/api/health")
def health():
    """Lightweight liveness + memory-backend reachability for judges/monitoring."""
    try:
        return {"ok": True, "engine": engine.status()}
    except Exception as e:  # never fail the health check
        return {"ok": False, "error": str(e)[:160]}


@app.get("/api/memories")
def list_memories(project: str | None = None):
    return {"memories": engine.list(project)}


@app.post("/api/memories")
def add_memory(req: AddReq):
    try:
        mem = engine.add(req.text, req.type, req.project, req.author)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"memory": mem}


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: str):
    if not engine.delete(memory_id):
        raise HTTPException(404, "not found")
    return {"ok": True}


@app.get("/api/graph")
def graph(project: str | None = None):
    return engine.graph(project)


@app.post("/api/search")
def search(req: SearchReq):
    t = time.perf_counter()
    res = engine.search(req.query, req.project)
    res["elapsed_ms"] = round((time.perf_counter() - t) * 1000)
    return res


@app.post("/api/recall")
def recall(req: RecallReq):
    t = time.perf_counter()
    res = engine.recall(req.project, req.task)
    res["elapsed_ms"] = round((time.perf_counter() - t) * 1000)
    return res


@app.post("/api/seed")
def reseed():
    seed.load_into(engine)
    return {"ok": True, "count": len(engine.list(None))}


@app.post("/api/reset")
def reset(project: str | None = None):
    engine.reset(project)
    return {"ok": True}


# --------------------------- static frontend ------------------------------- #

@app.get("/")
def index():
    idx = FRONTEND / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return {"service": "wheres-my-context", "engine": engine.status()}


APP_VIEWS = {"feed", "memories", "search", "graph", "ask", "settings"}


@app.get("/{view}")
def app_view(view: str):
    if view in APP_VIEWS:
        page = FRONTEND / "app.html"
        if page.exists():
            return FileResponse(page)
    asset = FRONTEND / view
    if asset.exists() and asset.is_file():
        return FileResponse(asset)
    return JSONResponse({"error": "not found"}, status_code=404)


# Serve the SPA locally. On Vercel the frontend is served as static assets, so
# guard this mount so importing the app never crashes if the dir isn't bundled.
if FRONTEND.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND), check_dir=False), name="static")
