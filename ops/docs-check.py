#!/usr/bin/env python3
"""Docs-drift guard: checks the numbers quoted in README/docs against the
repo's actual state (test count, migration count, e2e flow count).

Run it in the same breath as the suite:

    .venv/bin/python ops/docs-check.py

Exit 0 = docs agree with reality. Exit 1 = somewhere a number rotted.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ["README.md", "README.pt-PT.md", "docs/DEV_GUIDE.md",
        "docs/DEV_GUIDE.pt-PT.md", "docs/USER_GUIDE.md",
        "docs/USER_GUIDE.pt-PT.md"]


def actual_tests() -> int:
    out = subprocess.run(
        [str(ROOT / ".venv/bin/python"), "-m", "pytest", "--collect-only"],
        cwd=ROOT, capture_output=True, text=True).stdout
    n = sum(1 for line in out.splitlines() if "::" in line)
    if n:
        return n
    m = re.search(r"(\d+) tests? collected", out)
    if not m:
        raise SystemExit("could not read test count from pytest")
    return int(m.group(1))


def actual_migrations() -> int:
    return len(list((ROOT / "migrations").glob("*.sql")))


def actual_e2e() -> int:
    """Flows = ok(...) calls in the smoke suite, minus its own definition."""
    src = (ROOT / "e2e/smoke.mjs").read_text()
    return max(0, len(re.findall(r"\bok\(", src)) - 1)


def declared(text: str, patterns: list[str]) -> list[int]:
    found = []
    for pat in patterns:
        found += [int(m) for m in re.findall(pat, text)]
    return found


def main() -> int:
    tests, migs, e2e = actual_tests(), actual_migrations(), actual_e2e()
    print(f"actual: {tests} tests · {migs} migrations · {e2e} e2e flows")
    problems = []
    for rel in DOCS:
        p = ROOT / rel
        if not p.exists():
            continue
        text = p.read_text()
        t_nums = declared(text, [r"(\d+)\s+test(?:es|s)?\b", r"#\s*(\d+)\s+tests"])
        m_nums = declared(text, [r"[Mm]igra[çc][õo]es?\s*\((\d+)\)", r"\((\d+) migrations\)"])
        e_nums = declared(text, [r"(\d+)\s+(?:e2e\s+)?flows?", r"(\d+)\s+fluxos"])
        if t_nums and max(t_nums) != tests:
            problems.append(f"{rel}: tests quoted up to {max(t_nums)}, actual {tests}")
        if m_nums and max(m_nums) != migs:
            problems.append(f"{rel}: migrations quoted up to {max(m_nums)}, actual {migs}")
        if e_nums and max(e_nums) != e2e:
            problems.append(f"{rel}: e2e flows quoted up to {max(e_nums)}, actual {e2e}")
    if problems:
        print("\nDRIFT:")
        for x in problems:
            print(" -", x)
        return 1
    print("docs agree with the repo. nothing to fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
