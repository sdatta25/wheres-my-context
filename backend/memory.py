"""
Memory engines for *Where's My Context*.

The whole app talks to a single `MemoryEngine` interface so the frontend never
cares whether memory is backed by a local demo graph, self-hosted Cognee, or
Cognee Cloud. Swapping engines is a matter of environment variables.

    DemoEngine        — zero dependencies, builds a real co-occurrence knowledge
                        graph in-process. Great for demos and offline dev.
    CogneeHttpEngine  — talks to Cognee Cloud (or any Cognee server) over the
                        memory-native REST API (/remember, /recall). Keeps the
                        Demo graph as a local mirror for the live visualization
                        and as a graceful fallback if the backend is down.

Every engine returns the same shapes:

    memory  = {id, text, type, project, created_at, terms:[...]}
    graph   = {nodes:[{id,label,kind,size}], links:[{source,target,kind}]}
    search  = {answer, sources:[memory], path:[node_id], concepts:[str]}
"""
from __future__ import annotations

import os
import re
import time
import uuid
import threading
from dataclasses import dataclass, field, asdict
from typing import Optional

from . import cognee_cloud


# --------------------------------------------------------------------------- #
#  Lightweight, dependency-free knowledge extraction
# --------------------------------------------------------------------------- #

_STOP = set(
    """
    a an the and or but if then else for to of in on at by with from into over
    under as is are was were be been being do does did done have has had this
    that these those it its it's we you they he she i me my our your their them
    us not no yes can will would should could may might must shall about after
    before between during without within across per via than too very just also
    so such more most some any each all both few many much other same which who
    whom whose what when where why how here there because while against upon
    """.split()
)

# Domain keywords worth surfacing even when lower-cased in prose.
_TECH = [
    "postgres", "postgresql", "mongodb", "mongo", "redis", "sqlite", "kuzu",
    "lancedb", "neo4j", "qdrant", "pgvector", "docker", "kubernetes", "k8s",
    "fastapi", "flask", "django", "react", "vue", "svelte", "next.js", "node",
    "python", "typescript", "javascript", "rust", "go", "graphql", "rest",
    "grpc", "kafka", "rabbitmq", "s3", "lambda", "cognee", "openai", "claude",
    "anthropic", "llm", "rag", "embedding", "embeddings", "vector", "auth",
    "oauth", "jwt", "stripe", "webhook", "cache", "caching", "cron", "ci", "cd",
    "terraform", "aws", "gcp", "azure", "tailwind", "d3", "websocket", "sse",
]
_TECH_RE = re.compile(r"\b(" + "|".join(re.escape(t) for t in _TECH) + r")\b", re.I)

_TITLECASE_RE = re.compile(
    r"\b([A-Z][a-zA-Z0-9][a-zA-Z0-9+.\-]*(?:\s+[A-Z][a-zA-Z0-9+.\-]+){0,3})\b"
)
_QUOTED_RE = re.compile(r"[\"“]([^\"”]{2,48})[\"”]")
_HASHTAG_RE = re.compile(r"#(\w{2,32})")


def _canon(term: str) -> str:
    """Canonical key used to merge equivalent concepts."""
    t = term.strip().lower()
    t = re.sub(r"\s+", " ", t)
    aliases = {
        "postgresql": "postgres",
        "mongo": "mongodb",
        "k8s": "kubernetes",
        "embeddings": "embedding",
        "js": "javascript",
        "ts": "typescript",
    }
    return aliases.get(t, t)


def extract_terms(text: str) -> list[str]:
    """Pull salient concepts out of free text — no LLM required.

    Combines quoted phrases, #hashtags, TitleCase spans, and known tech terms,
    then de-duplicates on a canonical key while keeping a human-readable label.
    """
    found: dict[str, str] = {}

    def _add(label: str):
        label = label.strip(" .,:;()[]")
        if len(label) < 2:
            return
        key = _canon(label)
        if key in _STOP or len(key) < 2:
            return
        # keep the most informative (longest) surface form
        if key not in found or len(label) > len(found[key]):
            found[key] = label

    for m in _QUOTED_RE.findall(text):
        _add(m)
    for m in _HASHTAG_RE.findall(text):
        _add(m)
    for m in _TECH_RE.findall(text):
        _add(m.lower())
    for m in _TITLECASE_RE.findall(text):
        # drop leading stopword-y capitalized words at sentence start
        words = m.split()
        while words and _canon(words[0]) in _STOP:
            words = words[1:]
        if words:
            _add(" ".join(words))

    # keep a stable, ranked-ish order
    return list(dict.fromkeys(found.values()))


def _tokens(text: str) -> set[str]:
    return {
        _canon(w)
        for w in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9+.\-]*", text.lower())
        if _canon(w) not in _STOP and len(w) > 2
    }


# --------------------------------------------------------------------------- #
#  Data model
# --------------------------------------------------------------------------- #

@dataclass
class Memory:
    text: str
    type: str = "note"                 # note | decision | doc | code | fact
    project: str = "default"
    author: str = ""                   # who contributed it (the team-brain angle)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: float = field(default_factory=time.time)
    terms: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["snippet"] = (self.text[:160] + "…") if len(self.text) > 160 else self.text
        return d


# --------------------------------------------------------------------------- #
#  Base interface
# --------------------------------------------------------------------------- #

class MemoryEngine:
    name = "base"
    label = "Base"
    online = False  # whether it talks to a real Cognee backend

    def add(self, text: str, type: str = "note", project: str = "default", author: str = "") -> dict: ...
    def list(self, project: Optional[str] = None) -> list[dict]: ...
    def delete(self, memory_id: str) -> bool: ...
    def graph(self, project: Optional[str] = None) -> dict: ...
    def search(self, query: str, project: Optional[str] = None) -> dict: ...
    def recall(self, project: str, task: str = "") -> dict: ...
    def reset(self, project: Optional[str] = None) -> None: ...

    def status(self) -> dict:
        return {"engine": self.name, "label": self.label, "online": self.online}


# --------------------------------------------------------------------------- #
#  Demo engine — real graph, zero dependencies
# --------------------------------------------------------------------------- #

class DemoEngine(MemoryEngine):
    name = "demo"
    label = "Demo Engine (local graph)"
    online = False

    def __init__(self):
        self._lock = threading.RLock()
        self._mems: dict[str, Memory] = {}

    # -- writes ------------------------------------------------------------- #
    def add(self, text: str, type: str = "note", project: str = "default", author: str = "") -> dict:
        text = (text or "").strip()
        if not text:
            raise ValueError("empty memory")
        with self._lock:
            m = Memory(text=text, type=type or "note", project=project or "default",
                       author=(author or "").strip())
            m.terms = extract_terms(text)
            self._mems[m.id] = m
            return m.to_dict()

    def seed_add(self, text: str, type: str = "note", project: str = "default", author: str = "") -> dict:
        """Populate the local graph only (used for boot seed data). For the demo
        engine this is just add; cloud engines override it to skip the network."""
        return self.add(text, type, project, author)

    def delete(self, memory_id: str) -> bool:
        with self._lock:
            return self._mems.pop(memory_id, None) is not None

    def reset(self, project: Optional[str] = None) -> None:
        with self._lock:
            if project is None:
                self._mems.clear()
            else:
                for mid in [k for k, v in self._mems.items() if v.project == project]:
                    del self._mems[mid]

    # -- reads -------------------------------------------------------------- #
    def _scope(self, project: Optional[str]) -> list[Memory]:
        mems = list(self._mems.values())
        if project and project != "all":
            mems = [m for m in mems if m.project == project]
        return sorted(mems, key=lambda m: m.created_at, reverse=True)

    def list(self, project: Optional[str] = None) -> list[dict]:
        return [m.to_dict() for m in self._scope(project)]

    def projects(self) -> list[str]:
        return sorted({m.project for m in self._mems.values()})

    def graph(self, project: Optional[str] = None) -> dict:
        mems = self._scope(project)
        nodes: dict[str, dict] = {}
        links: list[dict] = []
        ent_count: dict[str, int] = {}
        author_count: dict[str, int] = {}

        for m in mems:
            for t in m.terms:
                ent_count[_canon(t)] = ent_count.get(_canon(t), 0) + 1
            if m.author:
                author_count[m.author] = author_count.get(m.author, 0) + 1

        for m in mems:
            nid = f"m:{m.id}"
            nodes[nid] = {
                "id": nid,
                "label": (m.text[:42] + "…") if len(m.text) > 42 else m.text,
                "kind": "memory",
                "mtype": m.type,
                "author": m.author,
                "size": 10,
            }
            # contributor (person) node → the team-brain: who added what
            if m.author:
                pid = f"p:{m.author}"
                if pid not in nodes:
                    nodes[pid] = {
                        "id": pid,
                        "label": m.author,
                        "kind": "person",
                        "size": 9 + 2 * author_count.get(m.author, 1),
                    }
                links.append({"source": pid, "target": nid, "kind": "by"})
            canon_terms = []
            for t in m.terms:
                key = _canon(t)
                eid = f"e:{key}"
                if eid not in nodes:
                    nodes[eid] = {
                        "id": eid,
                        "label": t,
                        "kind": "concept",
                        "size": 6 + 2 * ent_count.get(key, 1),
                    }
                links.append({"source": nid, "target": eid, "kind": "mentions"})
                canon_terms.append(key)
            # concept<->concept co-occurrence edges within a memory
            for i in range(len(canon_terms)):
                for j in range(i + 1, len(canon_terms)):
                    links.append(
                        {
                            "source": f"e:{canon_terms[i]}",
                            "target": f"e:{canon_terms[j]}",
                            "kind": "related",
                        }
                    )
        return {"nodes": list(nodes.values()), "links": links}

    def _rank(self, query: str, mems: list[Memory]) -> list[tuple[Memory, float, set]]:
        q_terms = {_canon(t) for t in extract_terms(query)}
        q_tokens = _tokens(query)
        scored = []
        for m in mems:
            m_terms = {_canon(t) for t in m.terms}
            m_tokens = _tokens(m.text)
            shared_terms = q_terms & m_terms
            shared_tokens = q_tokens & m_tokens
            score = 3.0 * len(shared_terms) + 1.0 * len(shared_tokens)
            # small boost for decisions — they're the "why"
            if m.type == "decision":
                score *= 1.15
            if score > 0:
                scored.append((m, score, shared_terms or {t for t in shared_tokens}))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def search(self, query: str, project: Optional[str] = None) -> dict:
        query = (query or "").strip()
        mems = self._scope(project)
        ranked = self._rank(query, mems)[:5]

        if not ranked:
            return {
                "answer": (
                    "I don't have anything in memory about that yet. Feed me a "
                    "note, decision, or doc and I'll remember it."
                ),
                "sources": [],
                "path": [],
                "concepts": [],
            }

        concepts, path = [], []
        lines = []
        for m, _score, shared in ranked:
            for s in shared:
                if s not in concepts:
                    concepts.append(s)
                path.append(f"e:{s}")
            path.append(f"m:{m.id}")
            tag = m.type.upper()
            lines.append(f"• [{tag}] {m.text}")

        connect = ", ".join(concepts[:6]) if concepts else "your notes"
        answer = (
            f"Here's the context I remember about “{query}”, connected through "
            f"**{connect}**:\n\n" + "\n".join(lines)
        )
        return {
            "answer": answer,
            "sources": [m.to_dict() for m, _s, _sh in ranked],
            "path": list(dict.fromkeys(path)),
            "concepts": concepts[:8],
        }

    def recall(self, project: str, task: str = "") -> dict:
        """Simulate the context an AI agent would get injected on a fresh session."""
        mems = self._scope(project)
        if task.strip():
            ranked = [m for m, _s, _sh in self._rank(task, mems)]
            if ranked:
                mems = ranked
        decisions = [m for m in mems if m.type == "decision"][:4]
        others = [m for m in mems if m.type != "decision"][:4]
        picked = decisions + others
        brief = "\n".join(f"- ({m.type}) {m.text}" for m in picked) or "- (nothing remembered yet)"
        header = f"Context brief for project “{project}”"
        if task.strip():
            header += f", task: “{task.strip()}”"
        return {
            "brief": f"{header}\n\n{brief}",
            "memories": [m.to_dict() for m in picked],
            "count": len(mems),
        }


# --------------------------------------------------------------------------- #
#  Cognee engine — real memory over the Cognee REST API (cloud or server)
# --------------------------------------------------------------------------- #

class CogneeHttpEngine(DemoEngine):
    """Persists to Cognee Cloud (or any Cognee server) via /remember + /recall,
    while keeping the in-process Demo graph as a local mirror.

    Why a mirror? Cognee owns the authoritative memory + cognified graph, but the
    REST API doesn't hand back node/edge ids that map onto our force-graph. So the
    mirror drives the *visualization* and gives an instant, offline-safe fallback,
    and Cognee provides the authoritative recall answer. Exactly the hybrid the
    official Claude Code plugin uses (server-first, local as degraded path).
    """
    name = "cognee_cloud"
    label = "Cognee Cloud"
    online = True

    def __init__(self, base_url: str, api_key: str, label: str = "Cognee Cloud", tenant_id: str = ""):
        super().__init__()
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or ""
        self.tenant_id = tenant_id or ""
        self.label = label
        self._health = {"reachable": None, "authed": None, "detail": "not checked"}
        self._health_at = 0.0

    # -- helpers ------------------------------------------------------------ #
    def _check(self, ttl: float = 20.0) -> dict:
        # Cache the ping so /api/status (hit on every UI refresh) stays snappy.
        if time.time() - self._health_at < ttl and self._health.get("reachable") is not None:
            return self._health
        try:
            self._health = cognee_cloud.ping(self.base_url, self.api_key, tenant_id=self.tenant_id)
        except Exception as e:  # never let a health check break the app
            self._health = {"reachable": False, "authed": False, "detail": str(e)[:120]}
        self._health_at = time.time()
        return self._health

    def status(self) -> dict:
        h = self._check()
        connected = bool(h.get("reachable"))
        return {
            "engine": self.name,
            "label": self.label + (" ✓" if connected and h.get("authed") else " (offline)"),
            "online": True,
            "connected": connected,
            "authed": bool(h.get("authed")),
            "base_url": self.base_url,
            "detail": h.get("detail"),
        }

    # -- helpers ------------------------------------------------------------ #
    # Namespace our datasets so recall never collides with other tenant data
    # (e.g. the Claude Code plugin's `agent_sessions`).
    _DS_PREFIX = "wmc_"

    def _ds(self, project: str) -> str:
        return f"{self._DS_PREFIX}{project or 'default'}"

    def _scoped_datasets(self, project) -> list:
        """Which cloud datasets a search should span: one project, or all of
        *our* known projects for the 'all' view — never the whole tenant."""
        if project and project != "all":
            return [self._ds(project)]
        return [self._ds(p) for p in self.projects()]

    # -- writes ------------------------------------------------------------- #
    def seed_add(self, text, type="note", project="default", author=""):
        # Boot seed data goes to the local mirror only — no cloud writes / cognify
        # cost on every restart. Live user adds still persist to Cognee Cloud.
        return DemoEngine.add(self, text, type, project, author)

    def add(self, text, type="note", project="default", author=""):
        rec = super().add(text, type, project, author)  # local mirror first (instant)
        try:
            # Bake the contributor into the cognified text so Cognee's graph links
            # people ↔ knowledge — enables team queries like "who knows about auth?".
            content = f"[Contributed by {author}] {text}" if author else text
            res = cognee_cloud.remember(
                self.base_url, self.api_key, content,
                dataset=self._ds(project), node_set=f"{project}:{type}",
                background=True, tenant_id=self.tenant_id,
            )
            rec["cognee"] = res
        except Exception as e:
            rec["cognee"] = {"error": str(e)[:160]}
        return rec

    # -- reads -------------------------------------------------------------- #
    def search(self, query, project=None):
        base = super().search(query, project)  # local answer + graph path/sources
        datasets = self._scoped_datasets(project)
        if not datasets:
            base["source_engine"] = "local_mirror"
            return base
        try:
            results = cognee_cloud.recall(
                self.base_url, self.api_key, query,
                datasets=datasets, tenant_id=self.tenant_id,
            )
        except Exception as e:
            results = {"error": str(e)[:160]}

        ctx = cognee_cloud.result_to_text(results) if isinstance(results, list) else ""
        if ctx.strip():
            base["answer"] = f"**Cognee Cloud** recalled this for “{query}”:\n\n{ctx}"
            base["source_engine"] = "cognee_cloud"
        else:
            # Empty / not-yet-cognified / error → keep the local mirror's answer.
            base["source_engine"] = "local_mirror"
            if isinstance(results, dict) and results.get("error"):
                base["cognee_note"] = results["error"]
            elif isinstance(results, list) and results:
                base["cognee_note"] = "cognify in progress — showing local mirror"
        return base


# --------------------------------------------------------------------------- #
#  Factory
# --------------------------------------------------------------------------- #

def build_engine() -> MemoryEngine:
    choice = os.getenv("MEMORY_ENGINE", "").strip().lower()

    # Cognee Cloud hands each team a dedicated instance URL at kickoff; accept
    # either COGNEE_CLOUD_URL (hackathon convention) or COGNEE_BASE_URL.
    def _cloud_url(default: str) -> str:
        return os.getenv("COGNEE_CLOUD_URL") or os.getenv("COGNEE_BASE_URL") or default

    tenant = os.getenv("COGNEE_TENANT_ID", "")

    if choice in ("cognee_cloud", "cloud"):
        base = _cloud_url("https://api.cognee.ai")
        key = os.getenv("COGNEE_API_KEY", "")
        return CogneeHttpEngine(base, key, label="Cognee Cloud", tenant_id=tenant)

    if choice in ("cognee", "server"):
        # Self-hosted Cognee server (the plugin's local API defaults to :8011).
        base = _cloud_url("http://localhost:8011")
        key = os.getenv("COGNEE_API_KEY", "")
        return CogneeHttpEngine(base, key, label="Cognee (server)", tenant_id=tenant)

    return DemoEngine()
