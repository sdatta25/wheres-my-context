#!/usr/bin/env bash
# One-command launcher for Where's My Context.
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  echo "→ creating virtualenv"
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "→ installing deps"
pip install -q -r requirements.txt

PORT="${PORT:-8000}"
echo "→ Where's My Context running at http://localhost:${PORT}"
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT}" "$@"
