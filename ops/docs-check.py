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


def actual_e2e() -> tuple[int, int]:
    """(flows, assertions) in the smoke suite: flow entries vs ok() asserts."""
    src = (ROOT / "e2e/smoke.mjs").read_text()
    flows = len(re.findall(r"^\s*name:\s*['\"]", src, re.M))
    asserts = max(0, len(re.findall(r"\bok\(", src)) - 1)
    return flows, asserts


def declared(text: str, patterns: list[str]) -> list[int]:
    found = []
    for pat in patterns:
        found += [int(m) for m in re.findall(pat, text)]
    return found


def main() -> int:
    tests, migs = actual_tests(), actual_migrations()
    e2e, e2e_asserts = actual_e2e()
    print(f"actual: {tests} tests · {migs} migrations · {e2e} e2e flows "
          f"({e2e_asserts} assertions)")
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
        a_nums = declared(text, [r"(\d+)\s+assertions?"])
        if a_nums and max(a_nums) != e2e_asserts:
            problems.append(
                f"{rel}: assertions quoted up to {max(a_nums)}, actual {e2e_asserts}")
    if problems:
        print("\nDRIFT:")
        for x in problems:
            print(" -", x)
        return 1
    print("docs agree with the repo. nothing to fix.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
