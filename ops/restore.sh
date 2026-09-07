#!/usr/bin/env bash
# BarSpec restore drill — put a snapshot back in place.
#
# Usage:  sudo ops/restore.sh backups/barspec-20260907-031700.db
#
# Stops the service, keeps the current db aside, restores the snapshot,
# starts the service and reports the resulting schema version.
set -euo pipefail
SNAP="${1:?usage: restore.sh <snapshot-file>}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DB="$REPO/barspec.db"

[ -f "$SNAP" ] || { echo "snapshot not found: $SNAP" >&2; exit 1; }

echo "Stopping barspec..."
systemctl stop barspec
SAVE="$DB.pre-restore-$(date +%Y%m%d-%H%M%S)"
cp "$DB" "$SAVE"
echo "current db kept at: $SAVE"
cp "$SNAP" "$DB"
echo "Starting barspec..."
systemctl start barspec
for i in $(seq 1 15); do
  journalctl -u barspec --since "20 seconds ago" -n 30 2>/dev/null | grep -q "Application startup complete" && break
  sleep 1
done
echo "Verify:"
python3 - "$DB" <<'EOF'
import sqlite3, sys
c = sqlite3.connect(sys.argv[1])
print("  user_version:", c.execute("PRAGMA user_version").fetchone()[0])
for t in ("specs", "stock_items", "spec_lines", "stock_takes"):
    print(f"  {t}:", c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
EOF
echo "Restore complete."
