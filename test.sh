#!/usr/bin/env bash
# Run the whole test suite (stdlib only — no pytest needed).
set -e
cd "$(dirname "$0")"
echo "▶ Where's My Context — test suite"
echo
echo "== engine tests =="
python3 -m tests.test_engine
echo
echo "== cognee cloud client + fallback tests =="
python3 -m tests.test_cognee_cloud
echo
echo "✅ All tests passed."
