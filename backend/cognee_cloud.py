"""
Minimal, dependency-free client for the Cognee memory-native REST API.

This speaks the exact transport contract that Cognee's official Claude Code
plugin uses (topoteretes/cognee-integrations → integrations/claude-code), so it
works against **Cognee Cloud** or any Cognee server:

    POST /api/v1/remember   multipart: datasetName, node_set, run_in_background,
                            data(file)                 → add + cognify in one call
    POST /api/v1/recall     json: {query, top_k, only_context, scope, datasets}
    GET  /api/v1/datasets/status?dataset=<id>&pipeline=cognify_pipeline

Auth is a single `X-Api-Key` header, attached only for remote (non-localhost)
targets — a local single-user server needs none. Stdlib only (urllib) so it has
no install footprint beyond the app itself.
"""
from __future__ import annotations

import json
import ssl
import uuid
import urllib.error
import urllib.parse
import urllib.request

UNREACHABLE = "UNREACHABLE"


def _ssl_context() -> ssl.SSLContext:
    """Default context; certifi if available (macOS often lacks a system bundle)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_CTX = _ssl_context()


def _is_local(url: str) -> bool:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0")


def _headers(base_url: str, api_key: str, tenant_id: str = "", extra: dict | None = None) -> dict:
    h = dict(extra or {})
    # The cloud credentials are meaningless to a local server, so only send them
    # to a remote target. Cognee Cloud tenants require BOTH headers.
    if not _is_local(base_url):
        if api_key:
            h["X-Api-Key"] = api_key
        if tenant_id:
            h["X-Tenant-Id"] = tenant_id
    return h


def _multipart(fields: dict, filename: str, content: bytes) -> tuple[bytes, str]:
    boundary = f"----wmc{uuid.uuid4().hex}"
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f"--{boundary}\r\n".encode())
        parts.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        parts.append(f"{value}\r\n".encode())
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        (
            f'Content-Disposition: form-data; name="data"; filename="{filename}"\r\n'
            "Content-Type: text/plain; charset=utf-8\r\n\r\n"
        ).encode()
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def _request(req: urllib.request.Request, timeout: float):
    """Return (raw_text, None) on success, or (None, error_dict/UNREACHABLE)."""
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_CTX) as resp:
            return resp.read().decode("utf-8"), None
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            msg = f"unauthorized (HTTP {e.code}) — check COGNEE_API_KEY"
        else:
            msg = f"server returned HTTP {e.code}"
        return None, {"error": msg, "status": e.code}
    except Exception as e:  # URLError / timeout / DNS → genuinely unreachable
        return None, {"error": f"unreachable: {str(e)[:160]}", "status": 0, "unreachable": True}


# --------------------------------------------------------------------------- #
#  Public API
# --------------------------------------------------------------------------- #

def remember(
    base_url: str,
    api_key: str,
    content: str,
    dataset: str = "default",
    node_set: str = "",
    background: bool = True,
    timeout: float = 60.0,
    tenant_id: str = "",
) -> dict:
    """POST /api/v1/remember. Returns {ok:True, dataset_id?, ...} or {error,...}."""
    url = base_url.rstrip("/") + "/api/v1/remember"
    body, boundary = _multipart(
        {
            "datasetName": dataset,
            "node_set": node_set or dataset,
            "run_in_background": "true" if background else "false",
        },
        filename=f"{(node_set or 'memory')}.txt",
        content=content.encode("utf-8"),
    )
    headers = _headers(base_url, api_key, tenant_id, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    raw, err = _request(req, timeout)
    if err is not None:
        return err
    try:
        data = json.loads(raw or "{}")
    except (json.JSONDecodeError, ValueError):
        return {"ok": True}
    if isinstance(data, dict) and data.get("error"):
        return {"error": str(data["error"])[:200], "status": 200}
    out = {"ok": True}
    if isinstance(data, dict):
        for k in ("dataset_id", "pipeline_run_id", "status"):
            if data.get(k):
                out[k] = str(data[k])
    return out


def recall(
    base_url: str,
    api_key: str,
    query: str,
    dataset: str = "",
    datasets: list | None = None,
    top_k: int = 5,
    scope: str = "auto",
    timeout: float = 20.0,
    tenant_id: str = "",
):
    """POST /api/v1/recall. Returns a list of context items, or an error dict.

    Scope the search with `datasets` (a list) or `dataset` (single). When both
    are empty the server searches the whole tenant — avoid that in the app so we
    don't pull in unrelated datasets (e.g. the Claude Code plugin's).
    """
    url = base_url.rstrip("/") + "/api/v1/recall"
    body = {"query": query, "top_k": top_k, "only_context": True, "scope": scope}
    ds_list = [d for d in (datasets or ([dataset] if dataset else [])) if d]
    if ds_list:
        body["datasets"] = ds_list
    headers = _headers(base_url, api_key, tenant_id, {"Content-Type": "application/json"})
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers, method="POST")

    raw, err = _request(req, timeout)
    if err is not None:
        return err
    try:
        data = json.loads(raw or "[]")
    except (json.JSONDecodeError, ValueError):
        return {"error": "malformed JSON from /api/v1/recall", "status": 200}
    if isinstance(data, dict) and data.get("error"):
        return {"error": str(data["error"])[:200], "status": 200}
    return data if isinstance(data, list) else [data]


def ping(base_url: str, api_key: str, timeout: float = 6.0, tenant_id: str = "") -> dict:
    """Lightweight reachability/auth check via a trivial recall.

    Returns {reachable: bool, authed: bool, detail: str}.
    """
    res = recall(base_url, api_key, "ping", top_k=1, timeout=timeout, tenant_id=tenant_id)
    if isinstance(res, list):
        return {"reachable": True, "authed": True, "detail": "ok"}
    status = res.get("status", 0)
    if res.get("unreachable"):
        return {"reachable": False, "authed": False, "detail": res.get("error", "unreachable")}
    if status in (401, 403):
        return {"reachable": True, "authed": False, "detail": res.get("error", "unauthorized")}
    # reachable, some other error (e.g. dataset) — still counts as connected
    return {"reachable": True, "authed": True, "detail": res.get("error", f"http {status}")}


import re

_NODE_RE = re.compile(r"__node_content_start__\n(.*?)\n__node_content_end__", re.S)
_CONN_RE = re.compile(r"^(.*?)\s--\[([^\]]+)\]-->\s(.*?)(?:\s{2,}\(.*)?$")


def _clean_label(s: str) -> str:
    # Cognee appends a bracketed keyword list to node labels; drop it + url-encoding.
    s = re.sub(r"\s*\[[^\]]*\]\s*$", "", s).strip()
    return s.replace("%3A", ":")


def format_recall(items: list) -> dict:
    """Turn Cognee recall results into {facts:[...], connections:[(a,rel,b)...]}.

    Cognee's GRAPH_COMPLETION `text` is a "Nodes:/Connections:" dump. We pull the
    human-readable node contents as grounded facts and the edges as connections,
    so the UI can show a clean answer *and* surface the graph relationships.
    Returns empty lists when nothing is cognified yet (guards the async gap).
    """
    facts: list[str] = []
    connections: list[tuple] = []
    for it in items:
        text = it.get("text", "") if isinstance(it, dict) else str(it)
        if not text or not text.strip():
            continue
        node_blocks = _NODE_RE.findall(text)
        if node_blocks:
            for b in node_blocks:
                b = b.strip()
                if b and b.lower() != "none" and len(b) > 3:
                    facts.append(b)
            after = re.split(r"\nConnections:\n", text, maxsplit=1)
            if len(after) > 1:
                for line in after[1].splitlines():
                    m = _CONN_RE.match(line.strip())
                    if m:
                        connections.append((_clean_label(m.group(1)), m.group(2), _clean_label(m.group(3))))
        else:
            facts.append(text.strip())  # plain (non-graph) result

    # de-dupe, keep order
    facts = list(dict.fromkeys(facts))
    seen, conns = set(), []
    for c in connections:
        if c not in seen:
            seen.add(c)
            conns.append(c)
    return {"facts": facts, "connections": conns}


def result_to_text(items: list) -> str:
    """Readable rendering of recall results (facts + a few graph connections)."""
    parsed = format_recall(items)
    out = [f"• {f}" for f in parsed["facts"]]
    if parsed["connections"]:
        out.append("")
        out.append("How it connects:")
        for a, rel, b in parsed["connections"][:6]:
            out.append(f"  {a} —[{rel}]→ {b}")
    return "\n".join(out).strip()
