# Where's My Context ◒

**Persistent AI memory that *connects* your context — powered by a knowledge graph.**

Built for the **Cognee "Where's My Context" hackathon** (June 29 – July 05, 2026).

AI agents forget everything the moment a session ends. *Where's My Context* is a
memory layer + second brain: you feed it notes, decisions, docs and code, it
builds a **knowledge graph** of the concepts inside them, and any agent (or you)
can later ask *"where's my context on X?"* and get a grounded answer that shows
**how** the pieces connect — plus exactly what context a fresh AI session gets
injected on wake-up.

It runs today on a built-in, zero-dependency **Demo Engine**, and drops straight
onto **Cognee** / **Cognee Cloud** by flipping two environment variables.

---

## ✨ What it does

- **Feed your brain** — capture notes, decisions, facts, docs, code per project.
- **Live knowledge graph** — concepts are extracted and linked; the D3
  force-graph grows as you add memories. Click any node to trace its context.
- **Ask your memory** — natural-language questions return grounded answers,
  the connecting concepts, and light up the exact path in the graph.
- **New AI session recall** — simulate the context brief an agent receives when
  it wakes up on a project (the literal answer to *"where's my context?"*).

## 🚀 Run it (30 seconds)

```bash
./run.sh                 # creates a venv, installs deps, serves on :8000
```

Then open **http://localhost:8000**. Demo data is seeded automatically, so the
graph is alive on first load. (Or run manually:
`pip install -r requirements.txt && uvicorn backend.main:app --reload`.)

## 🧠 Memory engines

The whole app talks to one `MemoryEngine` interface (`backend/memory.py`), so
the backend is swappable without touching the UI.

| Engine | How to enable | Notes |
| --- | --- | --- |
| **Demo** (default) | nothing | Real in-process co-occurrence graph, no keys, offline. |
| **Cognee Cloud** | `MEMORY_ENGINE=cognee_cloud` + `COGNEE_API_KEY` | Managed memory at `api.cognee.ai`. |
| **Cognee (server)** | `MEMORY_ENGINE=cognee` + `COGNEE_BASE_URL` | Any self-hosted Cognee API (plugin's local API is `:8011`). |

Copy `.env.example` → `.env` to configure.

### Cognee Cloud integration

`backend/cognee_cloud.py` is a small, stdlib-only client that speaks Cognee's
**memory-native REST API** — the exact contract used by Cognee's
[official Claude Code plugin](https://github.com/topoteretes/cognee-integrations):

| Call | Endpoint | Used for |
| --- | --- | --- |
| `remember()` | `POST /api/v1/remember` (multipart) | add **+** cognify in one call |
| `recall()`   | `POST /api/v1/recall` (json)        | authoritative search |
| `ping()`     | `POST /api/v1/recall` (top_k=1)     | health / auth check |

Auth is a single `X-Api-Key` header (sent only to remote targets). When
`MEMORY_ENGINE=cognee_cloud`, every `add` is persisted + cognified in the cloud
and every `Ask` is answered by Cognee's `recall`; the local graph stays as the
live visualization and an offline-safe fallback. Connection status shows in the
engine badge (`Cognee Cloud ✓` when reachable + authed).

> **Next:** point at a shared team dataset so every teammate's agent recalls
> from one graph.

## 🏗 Architecture

```
frontend/  index.html · styles.css · app.js   (vanilla + D3 force graph)
backend/   main.py     FastAPI routes + static hosting
           memory.py   MemoryEngine: Demo | Cognee | CogneeCloud
           seed.py     demo dataset
```

```
add ─▶ extract concepts ─▶ knowledge graph ─┬─▶ search  (grounded answer + path)
                                            └─▶ recall  (agent context brief)
```

## API

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/memories` | add + cognify a memory |
| `GET`  | `/api/memories` | list (optionally `?project=`) |
| `GET`  | `/api/graph` | nodes + links for the viz |
| `POST` | `/api/search` | ask a question |
| `POST` | `/api/recall` | new-session context brief |
| `GET`  | `/api/status` | active engine + projects |

## 👥 Team

Private repo — collaborators added via GitHub. Let's win that iPhone 17. 🏆
