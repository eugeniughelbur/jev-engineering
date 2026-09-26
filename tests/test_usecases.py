#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""The combine rules in each use case, pinned. No API key, no network.

    uv run tests/test_usecases.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent / "usecases"
for sub in ("inbox-triage", "slack-followups", "ai-writing-tells"):
    sys.path.insert(0, str(ROOT / sub))
sys.path.insert(0, str(ROOT))

from followups import needs_reply  # noqa: E402
from tells import SLOP, paragraphs_from_markdown  # noqa: E402
from triage import urgent  # noqa: E402

CASES = [
    ("mass mail is never urgent, whatever the scores",
     urgent({"human": 1, "waiting": 1, "cost": 1, "soon": 1}, True), False),
    ("a machine alert with a real cost is urgent",
     urgent({"human": 0.02, "waiting": 0.4, "cost": 0.8, "soon": 0.9}, False), True),
    ("a person waiting on you is urgent",
     urgent({"human": 0.8, "waiting": 0.9, "cost": 0.3, "soon": 0.2}, False), True),
    ("a salesperson 'waiting' is not, when it is not really personal",
     urgent({"human": 0.37, "waiting": 0.8, "cost": 0.1, "soon": 0.1}, False), False),
    ("already replied is off the list, whatever the scores",
     needs_reply({"asks_me": 0.99}, True), False),
    ("one strong check is enough to reply", needs_reply({"asks_me": 0.1, "blocked": 0.83}, False),
     True),
    ("a slop word is caught without a model", bool(SLOP.search("Let's delve into it.")), True),
    ("markdown headings and code are not prose",
     [p["text"] for p in paragraphs_from_markdown("# Title\n\nReal text.\n\n```\ncode\n```")],
     ["Real text."]),
]


def main() -> int:
    failures = 0
    for name, got, want in CASES:
        ok = got == want
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
    print(f"\n{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
