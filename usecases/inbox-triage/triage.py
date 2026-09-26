#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Sort an inbox into "needs me now" and everything else.

    uv run triage.py emails.example.json            # show the shortlist
    uv run triage.py emails.example.json --eval     # score against the labels

Input is a JSON list of emails with `id`, `from`, `subject`, `body` and
`list_unsubscribe`. Add `urgent: true/false` to score it.

"Is this urgent?" is the wrong question to ask a model. It means something
different to everyone. So it becomes four checks with plain definitions,
and the rule that combines them is ordinary code you can read and change.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from jevchecks import Check, report, run  # noqa: E402

CHECKS = [
    Check("human", "A real person wrote this message to the reader personally. "
                   "Newsletters, receipts, notifications and mass mail do not count."),
    Check("waiting", "Someone is waiting on the reader: they asked the reader for something, "
                     "are blocked by the reader, or need an answer from the reader."),
    Check("cost", "Ignoring this message for a day would cost the reader something real: "
                  "money, access, security, a deal, a deadline, or a person's trust."),
    Check("soon", "The message names a deadline or time limit within the next two days, "
                  "or asks for action now."),
]


def urgent(scores: dict[str, float], list_unsubscribe: bool) -> bool:
    # Mass mail is never urgent, and that needs no model at all.
    if list_unsubscribe:
        return False
    # A real cost is urgent on its own, even from a machine: a security
    # alert or a pager is not written by a person and still needs you now.
    if scores["cost"] >= 0.7:
        return True
    # Otherwise it takes a person who is waiting on you.
    return scores["human"] >= 0.5 and scores["waiting"] >= 0.6


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("emails", type=Path)
    p.add_argument("--eval", action="store_true", help="compare with the urgent labels")
    args = p.parse_args()

    emails = json.loads(args.emails.read_text())
    states = [{"from": e["from"], "subject": e["subject"], "body": e["body"]} for e in emails]
    results = run(states, CHECKS)

    rows, cost = [], 0.0
    for email, (scores, c) in zip(emails, results):
        cost += c
        rows.append({
            "id": email["id"], "label": email.get("urgent"),
            "predicted": urgent(scores, email.get("list_unsubscribe", False)),
            "scores": {k: round(v, 2) for k, v in scores.items()},
        })

    for r in sorted(rows, key=lambda r: not r["predicted"]):
        mark = "NOW " if r["predicted"] else "    "
        print(f"{mark}{r['id']:18} {r['scores']}")
    print(f"\nJev cost: ${cost:.5f} for {len(rows)} emails")
    if args.eval:
        print(json.dumps(report(rows), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
