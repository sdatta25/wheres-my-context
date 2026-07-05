# Where's My Context ◒

**Persistent AI memory that *connects* your context, powered by a knowledge graph.**

Built for the **Cognee "Where's My Context" hackathon** (June 29 to July 5, 2026).

### Try it live

**[wheres-my-context.vercel.app](https://wheres-my-context.vercel.app)** — running on Cognee Cloud. Ask *"why did we pick Postgres?"* or hit **Seed demo** to explore the graph.

---

AI agents forget everything the moment a session ends. *Where's My Context* is a persistent memory layer: you feed it notes, decisions, docs, and code, it builds a **knowledge graph** of the concepts inside them, and any agent (or person) can later ask *"where's my context on X?"* and get a grounded answer that shows how the pieces connect, plus exactly what context a fresh AI session gets injected on wake-up.

It runs out of the box on a built-in, zero-dependency **Demo Engine**, and switches to **Cognee Cloud** by setting two environment variables.

---

## What it does

- **Feed your brain.** Capture notes, decisions, facts, docs, and code per project.
- **Live knowledge graph.** Concepts are extracted and linked. The D3 force-graph grows as you add memories. Click any node to trace its context.
- **Ask your memory.** Natural-language questions return grounded answers with the connecting concepts highlighted in the graph.
- **Forgets vs. remembers.** A compare toggle shows a no-memory LLM's blank response next to Cognee's grounded answer, side by side.
- **Shared team brain.** Every memory records its contributor. People become nodes wired to what they added, so *"who set up the GraphQL gateway?"* returns the right teammate. Everyone on the same Cognee tenant reads and writes one graph.
- **New session recall.** Simulate the context brief a fresh AI agent receives on wake-up. That's the literal answer to *"where's my context?"*

---

## Quickstart (30 seconds)

```bash
./run.sh    # creates a venv, installs deps, serves on :8000
```

Open **http://localhost:8000**. Demo data is seeded automatically so the graph is live on first load.

Or manually:

```bash
pip install -r requirements.txt && uvicorn backend.main:app --reload
```

---

## Demo walkthrough

The core pitch: ask *"why did we pick Postgres?"* with the **Compare** toggle on. The generic LLM admits it has no memory. The Cognee answer cites the actual decision and traces the concept path in the graph. That contrast is the whole idea.

1. **The problem.** Open the app, enable **Compare: no-memory vs Cognee**, and ask a question about a past decision. The left side is blank; the right side is grounded.
2. **Watch memory form.** Set *Adding as* to your name and add a new decision. The knowledge graph grows instantly with a person node wired to the new concepts.
3. **Recall it.** Ask about the decision you just added. Cognee names you as the contributor and traces the path.
4. **Session recall.** Hit **Recall** under *New AI session* to see the exact context brief a fresh agent would receive on this project.

Every `add` is a `POST /api/v1/remember` to Cognee Cloud. Every `Ask` is a `POST /api/v1/recall`. Same contract as Cognee's official Claude Code plugin.

---

## Tests

Zero-dependency test suite covering the engine, extraction, search/recall, graceful degradation, and the Cognee Cloud client:

```bash
./test.sh
```

- `tests/test_engine.py` — extraction, scoping, graph build, search, recall
- `tests/test_cognee_cloud.py` — client request-building and fallback when Cognee is unreachable

Every Cognee call is wrapped so an outage silently falls back to the local mirror. The API returns clean JSON errors, never a raw stack trace. `GET /api/health` reports liveness and backend reachability.

---

## Deploy to Vercel

The repo is Vercel-ready (`vercel.json` + `api/index.py` serving the FastAPI app).

1. Push to GitHub, then import the repo on vercel.com. Framework preset: **Other**.
2. Add environment variables under **Settings > Environment Variables**:
   - `MEMORY_ENGINE = cognee_cloud`
   - `COGNEE_CLOUD_URL = https://tenant-<id>.aws.cognee.ai`
   - `COGNEE_TENANT_ID = <your-tenant-id>`
   - `COGNEE_API_KEY = <your-api-key>`
3. Deploy. The badge should read **Cognee Cloud ✓**.

> Serverless instances are ephemeral, so the local graph mirror resets on cold starts (seed data always shows). Persisted memory and recall live in Cognee Cloud, so answers stay grounded across deploys. For a persistent local mirror, a container host like Railway, Fly, or Render works with the same env vars.

---

## Memory engines

The app talks to one `MemoryEngine` interface (`backend/memory.py`), so the backend is fully swappable without touching the UI.

| Engine | How to enable | Notes |
|---|---|---|
| **Demo** (default) | nothing | Real in-process co-occurrence graph. No keys, works offline. |
| **Cognee Cloud** | `MEMORY_ENGINE=cognee_cloud` + cloud env vars | Live managed memory on a dedicated tenant. |
| **Cognee (self-hosted)** | `MEMORY_ENGINE=cognee` + `COGNEE_BASE_URL` | Any self-hosted Cognee API. |

Copy `.env.example` to `.env` to configure. Values come from the Cognee Cloud dashboard under API Keys > Connection Details.

### Cognee Cloud client

`backend/cognee_cloud.py` is a small stdlib-only client speaking Cognee's memory-native REST API, the same contract used by Cognee's [official Claude Code plugin](https://github.com/topoteretes/cognee-integrations):

| Call | Endpoint | Purpose |
|---|---|---|
| `remember()` | `POST /api/v1/remember` (multipart) | Add and cognify in one call |
| `recall()` | `POST /api/v1/recall` (json) | Authoritative search |
| `ping()` | `POST /api/v1/recall` (top_k=1) | Health and auth check |

Auth uses `X-Api-Key` and `X-Tenant-Id`. When `MEMORY_ENGINE=cognee_cloud`, every add is persisted and cognified in the cloud and every Ask is answered by Cognee's recall endpoint.

---

## Architecture

```
frontend/  index.html · styles.css · app.js   (vanilla JS + D3 force graph)
backend/   main.py     FastAPI routes + static hosting
           memory.py   MemoryEngine: Demo | Cognee | CogneeCloud
           seed.py     demo dataset
```

```
add -> extract concepts -> knowledge graph -> search  (grounded answer + path)
                                          -> recall  (agent context brief)
```

## API

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/api/memories` | Add and cognify a memory |
| `GET` | `/api/memories` | List memories (optionally `?project=`) |
| `GET` | `/api/graph` | Nodes and links for the visualization |
| `POST` | `/api/search` | Ask a question |
| `POST` | `/api/recall` | New-session context brief |
| `GET` | `/api/status` | Active engine and projects |

---

## Team

Built by [@sdatta25](https://github.com/sdatta25) and [@nadellasripad11](https://github.com/nadellasripad11).
