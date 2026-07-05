"""Tests for the core memory engine — the demo graph, extraction, ranking,
search, recall, and the API's graceful-degradation contract.

Runs with zero dependencies and no network:

    python -m tests.test_engine        # from the repo root
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.memory import DemoEngine, extract_terms, _canon  # noqa: E402


def check(name, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}")
    assert cond, name


def test_extraction():
    print("extraction")
    terms = [t.lower() for t in extract_terms(
        "We chose Postgres over Mongo because billing needs relational integrity."
    )]
    check("finds postgres", "postgres" in terms)
    check("canonicalizes mongo->mongodb", _canon("Mongo") == "mongodb")
    check("hashtag captured", any("refunds" in t.lower() for t in extract_terms("shipping #refunds soon")))
    check("quoted phrase captured", any("api gateway" in t.lower() for t in extract_terms('use the "API Gateway"')))
    check("empty text -> no terms", extract_terms("") == [])


def test_add_and_scope():
    print("add + scoping")
    e = DemoEngine()
    e.add("Chose Postgres for billing", "decision", "atlas", "Sourav")
    e.add("Redis powers the session cache", "note", "atlas", "Karam")
    e.add("Unrelated note", "note", "other", "Sripad")
    check("2 memories in atlas", len(e.list("atlas")) == 2)
    check("all projects lists 3", len(e.list(None)) == 3)
    check("projects tracked", set(e.projects()) == {"atlas", "other"})
    try:
        e.add("   ", "note", "atlas")
        check("empty add rejected", False)
    except ValueError:
        check("empty add rejected", True)


def test_graph():
    print("graph")
    e = DemoEngine()
    e.add("Chose Postgres over Mongo for billing", "decision", "atlas", "Sourav")
    g = e.graph("atlas")
    kinds = {n["kind"] for n in g["nodes"]}
    check("has memory nodes", "memory" in kinds)
    check("has concept nodes", "concept" in kinds)
    check("has person node (team brain)", "person" in kinds)
    check("has links", len(g["links"]) > 0)


def test_search():
    print("search")
    e = DemoEngine()
    e.add("We chose Postgres over Mongo because billing needs relational integrity.", "decision", "atlas")
    e.add("The frontend is built with D3 for the force graph.", "note", "atlas")
    res = e.search("why postgres?", "atlas")
    check("answer mentions postgres", "postgres" in res["answer"].lower())
    check("has sources", len(res["sources"]) >= 1)
    check("has a graph path", len(res["path"]) >= 1)
    empty = e.search("quantum teleportation budget", "atlas")
    check("no-hit search degrades gracefully", empty["sources"] == [])


def test_recall():
    print("recall (new-session brief)")
    e = DemoEngine()
    e.add("Chose Postgres for billing", "decision", "atlas")
    e.add("Deploys run on Railway", "note", "atlas")
    r = e.recall("atlas", "add refunds")
    check("brief is non-empty", len(r["brief"]) > 0)
    check("brief prioritizes decisions", "decision" in r["brief"] or "Postgres" in r["brief"])
    check("count reported", r["count"] == 2)


def main():
    tests = [test_extraction, test_add_and_scope, test_graph, test_search, test_recall]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} engine test groups passed ✅")


if __name__ == "__main__":
    main()
