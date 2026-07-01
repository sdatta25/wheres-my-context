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
- **Forgets vs. remembers** — a compare toggle shows a no-memory LLM's blank
  stare next to Cognee's grounded answer, side by side.
- **Shared team brain** — set who you are; every memory records its contributor,
  people become nodes wired to what they added, and attribution is baked into the
  cognified graph so *"who set up the GraphQL gateway?"* returns the right teammate.
  Everyone on the same Cognee tenant reads and writes one graph.
- **New AI session recall** — simulate the context brief an agent receives when
  it wakes up on a project (the literal answer to *"where's my context?"*).

## 🎬 Demo script (2 minutes, for judges)

> The pitch in one sentence: **AI forgets the moment a session ends — Where's My
> Context gives it a knowledge-graph memory that persists and *connects*.**

1. **The problem (10s).** Open the app. Tick **⚔️ Compare: no-memory vs Cognee**
   in the Ask panel. Ask *"why did we pick Postgres?"* → the **❌ Generic LLM**
   bubble admits it has no memory; the **✅ With Cognee** bubble answers with the
   real decision *and* shows how concepts connect. That contrast is the whole pitch.
2. **Watch memory form (30s).** Set *Adding as* to your name. In **Feed your
   brain**, add a decision, e.g. *"We're moving auth to Auth0 next sprint; Sarah
   leads it."* The **knowledge graph** grows instantly — a new **person node**
   (you) wires to the memory, plus concept nodes — and the badge shows
   **`Cognee Cloud ✓`**: it just persisted + cognified on a live Cognee tenant.
   Point out the orange contributor nodes: this is a **shared team brain**.
   Ask *"who set up X?"* → Cognee names the teammate who added it.
3. **Recall it (30s).** Ask *"what's changing with auth and who owns it?"* → a
   grounded answer sourced from Cognee's graph, tracing the path in the viz.
4. **"Where's my context?" (30s).** Hit **Recall** under *New AI session* → see
   the exact context brief a fresh AI agent gets injected on wake-up. That's the
   theme, literally: no more starting from zero.
5. **Proof it's real (10s).** Every live add is a `POST /api/v1/remember` to
   `…aws.cognee.ai`; every answer is a `POST /api/v1/recall`. Same contract as
   Cognee's official Claude Code plugin.

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
| **Cognee Cloud** ✅ | `MEMORY_ENGINE=cognee_cloud` + `COGNEE_CLOUD_URL` + `COGNEE_TENANT_ID` + `COGNEE_API_KEY` | **Live** — managed memory on your dedicated tenant instance. |
| **Cognee (server)** | `MEMORY_ENGINE=cognee` + `COGNEE_BASE_URL` | Any self-hosted Cognee API (plugin's local API is `:8011`). |

Copy `.env.example` → `.env` to configure (values come straight from the Cognee
Cloud dashboard → API Keys → *Connection Details*).

### Cognee Cloud integration

`backend/cognee_cloud.py` is a small, stdlib-only client that speaks Cognee's
**memory-native REST API** — the exact contract used by Cognee's
[official Claude Code plugin](https://github.com/topoteretes/cognee-integrations):

| Call | Endpoint | Used for |
| --- | --- | --- |
| `remember()` | `POST /api/v1/remember` (multipart) | add **+** cognify in one call |
| `recall()`   | `POST /api/v1/recall` (json)        | authoritative search |
| `ping()`     | `POST /api/v1/recall` (top_k=1)     | health / auth check |

Auth uses `X-Api-Key` **and** `X-Tenant-Id` (both sent only to remote targets;
`certifi` supplies the CA bundle so HTTPS verifies on macOS). When
`MEMORY_ENGINE=cognee_cloud`, every `add` is persisted + cognified in the cloud
and every `Ask` is answered by Cognee's `recall` — the response's graph
`Nodes:/Connections:` are parsed into a clean grounded answer plus a "how it
connects" view. The local graph stays as the live visualization and an
offline-safe fallback (used automatically while a fresh write is still
cognifying). Connection status shows in the engine badge (`Cognee Cloud ✓`).

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
