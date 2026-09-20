#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Pool decisions across a team, so the rules get better with more people.

Everyone still decides locally. Nothing central runs. Each person pushes a
redacted copy of their decision log into a shared folder, usually a checked-out
git repo, and calibration can then fit thresholds on the whole team instead of
one laptop.

    export JEV_POOL_DIR=~/work/team-policy/pool
    uv run pool.py push          write your redacted log into the pool
    uv run pool.py status        what the pool holds and who contributed
    uv run pool.py redact-check  show exactly what leaving your machine looks like

Redaction runs before anything is written, and `redact-check` prints the result
so you can see it rather than trust it. Commands carry secrets, paths and
customer names, and a pool that leaks those is worse than no pool.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import socket
import sys
from collections import Counter
from pathlib import Path

from jev_gate import LOG

POOL = Path(os.environ.get("JEV_POOL_DIR", "")).expanduser() if os.environ.get("JEV_POOL_DIR") else None
HOME = str(Path.home())

# Anything matching these never leaves the machine. Order matters: longest first.
REDACTIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(sk|rk|pk)[-_](live|test|or)[-_][A-Za-z0-9_\-]{6,}"), "<KEY>"),
    (re.compile(r"\b(gh[pousr]|github_pat)_[A-Za-z0-9_]{10,}"), "<KEY>"),
    (re.compile(r"\bAKIA[0-9A-Z]{12,}"), "<KEY>"),
    (re.compile(r"\bxox[abps]-[A-Za-z0-9-]{10,}"), "<KEY>"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), "<JWT>"),
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<EMAIL>"),
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), "<HEX>"),
    (re.compile(r"(--?(?:password|token|secret|api[-_]?key)[= ])\S+", re.I), r"\1<REDACTED>"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "<IP>"),
]


def redact(command: str) -> str:
    out = command.replace(HOME, "~")
    for pattern, replacement in REDACTIONS:
        out = pattern.sub(replacement, out)
    return out[:300]


def contributor() -> str:
    """A stable, non-identifying handle, so a pool shows breadth without names."""
    seed = f"{getpass.getuser()}@{socket.gethostname()}"
    return hashlib.sha256(seed.encode()).hexdigest()[:10]


def read_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def shareable(rows: list[dict]) -> list[dict]:
    """Only the fields calibration needs. No cwd, no transcript, no raw command."""
    return [
        {
            "at": r.get("at", "")[:10],  # date only, not the hour someone worked
            "command": redact(r.get("command", "")),
            "verdict": r.get("verdict"),
            "source": r.get("source"),
            "destructive": r.get("destructive"),
            "confidence": r.get("confidence"),
        }
        for r in rows
    ]


def require_pool() -> Path:
    if not POOL:
        print("set JEV_POOL_DIR to a shared folder, usually a checked-out git repo", file=sys.stderr)
        print("example: export JEV_POOL_DIR=~/work/team-policy/pool", file=sys.stderr)
        raise SystemExit(1)
    POOL.mkdir(parents=True, exist_ok=True)
    return POOL


def push() -> int:
    pool = require_pool()
    rows = shareable(read_log(LOG))
    if not rows:
        print(f"nothing to push, {LOG} is empty")
        return 0
    target = pool / f"{contributor()}.jsonl"
    target.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    print(f"wrote {len(rows)} redacted decisions to {target}")
    print("commit and push that folder to share it")
    return 0


def status() -> int:
    pool = require_pool()
    files = sorted(pool.glob("*.jsonl"))
    if not files:
        print(f"pool at {pool} is empty")
        return 0
    total = 0
    verdicts: Counter[str] = Counter()
    for path in files:
        rows = read_log(path)
        total += len(rows)
        verdicts.update(r.get("verdict", "?") for r in rows)
        marker = "  (you)" if path.stem == contributor() else ""
        print(f"  {path.stem}  {len(rows):5} decisions{marker}")
    print(f"\n{len(files)} contributor(s), {total} decisions")
    print(f"verdicts: {dict(verdicts)}")
    print("\nFit thresholds on all of it:  uv run calibrate.py --pool")
    return 0


def redact_check() -> int:
    rows = read_log(LOG)
    if not rows:
        print(f"{LOG} is empty, nothing to show")
        return 0
    print("This is exactly what would leave your machine.\n")
    for original, cleaned in list(zip(rows, shareable(rows)))[-15:]:
        before = original.get("command", "")
        after = cleaned["command"]
        flag = "  CHANGED" if before[:300] != after else ""
        print(f"  before: {before[:88]}")
        print(f"  after : {after[:88]}{flag}\n")
    print("Fields shared: date, redacted command, verdict, source, probability, confidence.")
    print("Fields never shared: working directory, time of day, username, hostname.")
    return 0


def load_pool() -> list[dict]:
    """Used by calibrate.py --pool."""
    if not POOL or not POOL.exists():
        return []
    rows: list[dict] = []
    for path in sorted(POOL.glob("*.jsonl")):
        rows.extend(read_log(path))
    return rows


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "status"
    if action == "push":
        return push()
    if action == "status":
        return status()
    if action in ("redact-check", "check"):
        return redact_check()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
