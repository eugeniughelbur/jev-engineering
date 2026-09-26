#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Find the Slack messages that are waiting on you, across every channel.

    uv run followups.py messages.example.json --me alex --eval

Input is a JSON list with `id`, `channel`, `author`, `text` and
`you_replied_after`. Export it from the Slack API, or have your agent do it.

Three checks decide it, and one fact decides it before any model runs: if
you already replied later in the thread, it is off the list.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from jevchecks import Check, report, run  # noqa: E402


def checks(me: str) -> list[Check]:
    return [
        Check("asks_me", f"The message asks {me} a question or asks {me} to do something. "
                         f"A question to a whole channel, or to someone else, does not count."),
        Check("decision", f"The message needs {me} to decide, approve, review or confirm "
                          f"something before the author can go on."),
        Check("blocked", f"The author, a customer or a team is stuck or losing something "
                         f"until {me} responds."),
    ]


def needs_reply(scores: dict[str, float], replied: bool) -> bool:
    if replied:
        return False
    return max(scores.values()) >= 0.6


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("messages", type=Path)
    p.add_argument("--me", required=True, help="your Slack name, as others mention you")
    p.add_argument("--eval", action="store_true", help="compare with the needs_reply labels")
    args = p.parse_args()

    messages = json.loads(args.messages.read_text())
    # Only messages you have not answered reach the model.
    open_items = [m for m in messages if not m.get("you_replied_after")]
    states = [{"reader": args.me, "channel": m["channel"], "author": m["author"],
               "message": m["text"]} for m in open_items]
    scored = dict(zip((m["id"] for m in open_items), run(states, checks(args.me))))

    rows, cost = [], 0.0
    for m in messages:
        scores, c = scored.get(m["id"], ({}, 0.0))
        cost += c
        rows.append({"id": m["id"], "label": m.get("needs_reply"),
                     "predicted": needs_reply(scores, m.get("you_replied_after", False)),
                     "scores": {k: round(v, 2) for k, v in scores.items()}})

    for r in sorted(rows, key=lambda r: not r["predicted"]):
        print(f"{'REPLY' if r['predicted'] else '     '} {r['id']:20} {r['scores']}")
    print(f"\nJev cost: ${cost:.5f} for {len(open_items)} unanswered messages")
    if args.eval:
        print(json.dumps(report(rows), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
