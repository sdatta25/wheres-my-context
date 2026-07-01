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


def _headers(base_url: str, api_key: str, extra: dict | None = None) -> dict:
    h = dict(extra or {})
    # The cloud key is meaningless to a local server, so only send it remotely.
    if api_key and not _is_local(base_url):
        h["X-Api-Key"] = api_key
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
    headers = _headers(base_url, api_key, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
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
    top_k: int = 5,
    scope: str = "auto",
    timeout: float = 20.0,
):
    """POST /api/v1/recall. Returns a list of context items, or an error dict."""
    url = base_url.rstrip("/") + "/api/v1/recall"
    body = {"query": query, "top_k": top_k, "only_context": True, "scope": scope}
    if dataset:
        body["datasets"] = [dataset]
    headers = _headers(base_url, api_key, {"Content-Type": "application/json"})
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


def ping(base_url: str, api_key: str, timeout: float = 6.0) -> dict:
    """Lightweight reachability/auth check via a trivial recall.

    Returns {reachable: bool, authed: bool, detail: str}.
    """
    res = recall(base_url, api_key, "ping", top_k=1, timeout=timeout)
    if isinstance(res, list):
        return {"reachable": True, "authed": True, "detail": "ok"}
    status = res.get("status", 0)
    if res.get("unreachable"):
        return {"reachable": False, "authed": False, "detail": res.get("error", "unreachable")}
    if status in (401, 403):
        return {"reachable": True, "authed": False, "detail": res.get("error", "unauthorized")}
    # reachable, some other error (e.g. dataset) — still counts as connected
    return {"reachable": True, "authed": True, "detail": res.get("error", f"http {status}")}


def result_to_text(items: list) -> str:
    """Flatten recall results (strings or dicts) into readable context text."""
    lines = []
    for it in items:
        if isinstance(it, str):
            lines.append(it.strip())
        elif isinstance(it, dict):
            txt = it.get("text") or it.get("content") or it.get("value") or it.get("name")
            lines.append(str(txt).strip() if txt else json.dumps(it)[:200])
        else:
            lines.append(str(it))
    return "\n".join(f"• {ln}" for ln in lines if ln)
