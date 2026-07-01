"""Tests for the Cognee Cloud integration.

Runs without a real Cognee backend: it exercises the client's request-building
and the engine's graceful fallback when the server is unreachable. Run:

    python -m tests.test_cognee_cloud     # from the repo root
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend import cognee_cloud as cc  # noqa: E402
from backend.memory import CogneeHttpEngine, build_engine  # noqa: E402

# A port that refuses fast, so "unreachable" paths return promptly.
DEAD = "http://127.0.0.1:9"


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    assert cond, name


def test_helpers():
    print("helpers")
    check("localhost is local", cc._is_local("http://localhost:8011"))
    check("127.0.0.1 is local", cc._is_local("http://127.0.0.1:9"))
    check("cloud is not local", not cc._is_local("https://api.cognee.ai"))

    # X-Api-Key only attached to remote targets
    check("key sent to cloud", "X-Api-Key" in cc._headers("https://api.cognee.ai", "ck_x"))
    check("key withheld from local", "X-Api-Key" not in cc._headers("http://localhost:8011", "ck_x"))

    body, boundary = cc._multipart({"datasetName": "atlas", "run_in_background": "true"}, "m.txt", b"hi")
    check("multipart has boundary", boundary.encode() in body)
    check("multipart has field", b'name="datasetName"' in body and b"atlas" in body)
    check("multipart has file", b'filename="m.txt"' in body and b"hi" in body)

    txt = cc.result_to_text(["alpha", {"text": "beta"}, {"name": "gamma"}])
    check("flatten strings", "• alpha" in txt)
    check("flatten dict.text", "• beta" in txt)
    check("flatten dict.name", "• gamma" in txt)


def test_unreachable_client():
    print("client against a dead endpoint")
    r = cc.remember(DEAD, "ck_x", "hello", dataset="atlas")
    check("remember returns error dict", isinstance(r, dict) and "error" in r)
    check("remember marks unreachable", r.get("unreachable") is True)

    s = cc.recall(DEAD, "ck_x", "why postgres?", dataset="atlas")
    check("recall returns error dict", isinstance(s, dict) and "error" in s)

    p = cc.ping(DEAD, "ck_x")
    check("ping reports not reachable", p["reachable"] is False)


def test_engine_fallback():
    print("engine graceful fallback")
    eng = CogneeHttpEngine(DEAD, "ck_x", label="Cognee Cloud")
    # seed a couple memories — local mirror must still work fully
    rec = eng.add("We chose Postgres over Mongo for billing integrity.", "decision", "atlas")
    eng.add("Sarah owns the Stripe billing webhook.", "note", "atlas")

    mems = eng.list("atlas")
    check("add kept local mirror", len(mems) == 2)
    check("add attempted cognee write", "cognee" in rec and "error" in rec["cognee"])

    g = eng.graph("atlas")
    check("graph has nodes", len(g["nodes"]) > 2)

    res = eng.search("why postgres?", "atlas")
    check("search still answers via mirror", bool(res["answer"]))
    check("search flags mirror fallback", res.get("source_engine") == "local_mirror")
    check("search found the decision", any("Postgres" in s["text"] for s in res["sources"]))

    st = eng.status()
    check("status engine name", st["engine"] == "cognee_cloud")
    check("status connected False", st["connected"] is False)
    check("status base_url", st["base_url"] == DEAD)


def test_factory():
    print("factory")
    os.environ.pop("MEMORY_ENGINE", None)
    check("default is demo", build_engine().name == "demo")
    os.environ["MEMORY_ENGINE"] = "cognee_cloud"
    os.environ["COGNEE_BASE_URL"] = DEAD
    eng = build_engine()
    check("cloud selected", eng.name == "cognee_cloud")
    check("cloud base_url from env", eng.base_url == DEAD)
    os.environ.pop("MEMORY_ENGINE", None)
    os.environ.pop("COGNEE_BASE_URL", None)


if __name__ == "__main__":
    for t in (test_helpers, test_unreachable_client, test_engine_fallback, test_factory):
        t()
    print("\nAll Cognee Cloud integration tests passed ✓")
