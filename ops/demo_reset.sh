#!/usr/bin/env bash
# Reset the BarSpec demo to a fresh, deterministic month.
#   ops/demo_reset.sh            # reseed + restart the demo service
#   DEMO_DB=/tmp/x.db ops/demo_reset.sh
set -euo pipefail

REPO="${REPO:-/home/vitor/dev/barspec}"
DB="${DEMO_DB:-/var/lib/barspec-demo/demo.db}"
if [ -x "$REPO/.venv/bin/python" ]; then PY="${PY:-$REPO/.venv/bin/python}"; else PY="${PY:-/usr/bin/python3}"; fi
UNIT="barspec-demo"

cd "$REPO"

# 1) wipe the DB *and* its WAL sidecars (a crashed run leaves stale .db-wal/-shm)
rm -f "$DB" "$DB-wal" "$DB-shm"
mkdir -p "$(dirname "$DB")"

# 2) seed the fictional venue + a full month of use (deterministic)
BARSPEC_DB="$DB" "$PY" ops/seed_demo.py --month

# 3) restart the demo so it picks up the new file
if systemctl list-unit-files 2>/dev/null | grep -q "^${UNIT}.service"; then
  # non-interactive sudo only: never hang waiting for a password
  if sudo -n systemctl restart "$UNIT" 2>/dev/null; then
    sleep 3
    systemctl is-active "$UNIT"
  else
    echo "seeded OK. Now restart the demo service yourself (needs root):"
    echo "    sudo systemctl restart $UNIT"
  fi
else
  pkill -f "[u]vicorn main:app.*8791" || true
  sleep 1
  (cd "$REPO" && BARSPEC_DB="$DB" nohup "$PY" -m uvicorn main:app \
      --host 0.0.0.0 --port 8791 >/tmp/barspec-demo.log 2>&1 &)
  sleep 4
fi

curl -s -o /dev/null -w "demo :8791 -> %{http_code}\n" http://127.0.0.1:8791/ || true
echo "demo reset: $(du -h "$DB" | cut -f1) DB at $DB (owner PIN 1234 / staff PIN 2468)"
