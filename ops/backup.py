#!/usr/bin/env python3
"""Nightly BarSpec backup — sqlite .backup() + integrity check + rotation.

Safe against a live writer (sqlite online backup API). Keeps the 14 most
recent snapshots, logs every run. Run by barspec-backup.timer (03:17 daily)
as user vitor.

Usage:  python3 ops/backup.py            (snapshot + prune + log)
Env:    BARSPEC_DB  override source db (default: repo barspec.db)
"""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("BARSPEC_DB", REPO / "barspec.db"))
OUT = REPO / "backups"
KEEP = 14  # snapshots retained
LOG = OUT / "backup.log"


def log(line: str) -> None:
    try:
        with LOG.open("a") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}  {line}\n")
    except OSError:
        pass


def main() -> int:
    if not DB.exists():
        log(f"FAIL  source db missing: {DB}")
        return 1
    OUT.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = OUT / f"barspec-{stamp}.db"
    try:
        src = sqlite3.connect(str(DB))
        dst = sqlite3.connect(str(target))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
    except sqlite3.Error as e:
        log(f"FAIL  {DB.name} -> {target.name}: {e}")
        return 1
    # integrity on the COPY (proves the snapshot is readable, not just written)
    try:
        c = sqlite3.connect(str(target))
        ok = c.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        c.close()
    except sqlite3.Error:
        ok = False
    size = target.stat().st_size
    if not ok:
        log(f"FAIL  integrity_check on {target.name}")
        target.unlink(missing_ok=True)
        return 1
    # rotate: newest KEEP survive
    snaps = sorted(OUT.glob("barspec-*.db"))
    for old in snaps[:-KEEP]:
        old.unlink()
    pruned = len(snaps) - KEEP if len(snaps) > KEEP else 0
    log(f"OK    {DB.name} -> {target.name}  {size:,} B  integrity ok  kept={min(len(snaps), KEEP)} pruned={pruned}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
