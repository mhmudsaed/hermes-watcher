#!/usr/bin/env bash
# Offline demo: full cycle against fixture payloads, prints the rendered digest.
# No network, no credentials. Usage: scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."

PY=.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "missing .venv — run: uv venv .venv && uv pip install --python .venv/bin/python -e '.[test]'" >&2
  exit 1
fi

export WATCHER_DB="${WATCHER_DB:-/tmp/watcher-demo.db}"
export WATCHER_PROFILE="${WATCHER_PROFILE:-profiles/default.yaml}"
export WATCHER_SOURCES="${WATCHER_SOURCES:-remoteok,weworkremotely,remotive,arbeitnow}"
export WATCHER_MIN_INTERVAL=0
rm -f "$WATCHER_DB"

echo "=== 1/3 pytest (offline) ==="
$PY -m pytest -q

echo
echo "=== 2/3 fixture-backed cycle (fake HTTP + FakeSender) ==="
$PY - "$WATCHER_DB" <<'EOF'
import sys
sys.path.insert(0, ".")
import httpx
from watcher.config import Settings
from watcher.notify import FakeSender
from watcher.runner import run_once
from watcher.store import Store

db = sys.argv[1]
FIX = "tests/fixtures/"
mapping = {
    "remoteok.com/api": open(FIX + "remoteok.json", "rb").read(),
    "programming-jobs.rss": open(FIX + "weworkremotely.xml", "rb").read(),
    "remotive.com/api": open(FIX + "remotive.json", "rb").read(),
    "arbeitnow.com/api": open(FIX + "arbeitnow.json", "rb").read(),
}

def handler(request: httpx.Request) -> httpx.Response:
    for key, payload in mapping.items():
        if key in str(request.url):
            return httpx.Response(200, content=payload)
    return httpx.Response(404, content=b"no fixture")

s = Settings(db_path=db, min_interval_seconds=0)
store = Store(db)
try:
    r1 = run_once(s, sender=FakeSender(), client=httpx.Client(transport=httpx.MockTransport(handler)), store=store)
    print("cycle 1:", r1.summary(), file=sys.stderr)
    r2 = run_once(s, sender=FakeSender(), client=httpx.Client(transport=httpx.MockTransport(handler)), store=store)
    print("cycle 2 (rerun, expect zero new):", r2.summary(), file=sys.stderr)
finally:
    store.close()
EOF

echo
echo "=== 3/3 CLI: stats + sources ==="
WATCHER_DB="$WATCHER_DB" $PY -m watcher.cli stats
