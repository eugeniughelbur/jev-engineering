#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Flag paragraphs that read like AI wrote them, and say which tell.

    uv run tells.py paragraphs.example.json --eval
    uv run tells.py draft.md                 # a markdown file, one check per paragraph

"Does this sound like AI?" is too vague to score. So it becomes separate
tells. The mechanical ones, like slop words, are plain regex and cost nothing.
The structural ones, like "not X but Y" or a run of three fragments, go to Jev,
one question per tell, all in one request per paragraph.

Built for an agent loop: draft, run this, rewrite what it flags, repeat.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from jevchecks import Check, report, run  # noqa: E402

# Free tells. A hit on any of these flags the paragraph without a model call.
SLOP = re.compile(
    r"\b(delve|leverage|seamless(ly)?|robust|unlock|game[- ]changer|cutting[- ]edge|"
    r"ever[- ]evolving|fast[- ]paced|landscape|tapestry|empower|foster|navigate the|"
    r"in conclusion|it'?s worth noting|hope this helps|great question)\b",
    re.IGNORECASE,
)

# Tells that need judgement. Each is one yes/no question.
CHECKS = [
    Check("negative_parallel", "The paragraph uses a 'not X, but Y' or 'it isn't just X, it's Y' "
                               "construction to sound profound."),
    Check("tricolon", "The paragraph lists three short parallel items or sentence fragments "
                      "for rhythm rather than information, like 'Faster. Smarter. Better.'"),
    Check("generic", "The paragraph makes broad claims with no concrete detail: no names, numbers, "
                     "dates, or specific events. It could be about almost anything."),
    Check("assistant_voice", "The paragraph talks like a chatbot to its user: praising the question, "
                             "offering help, or wishing the reader well."),
    Check("hedge", "The paragraph hedges without committing to anything, like 'results may vary' "
                   "or 'it depends on your unique needs'."),
]
FLAG_ABOVE = 0.7


def paragraphs_from_markdown(text: str) -> list[dict]:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    # Headings, code and lists are not prose.
    prose = [b for b in blocks if not b.startswith(("#", "```", "- ", "* ", "|", ">"))]
    return [{"id": f"p{i + 1}", "text": b} for i, b in enumerate(prose)]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("source", type=Path, help="a JSON list of {id, text} or a markdown file")
    p.add_argument("--eval", action="store_true", help="compare with the ai labels")
    args = p.parse_args()

    raw = args.source.read_text()
    items = json.loads(raw) if args.source.suffix == ".json" else paragraphs_from_markdown(raw)
    results = run([{"paragraph": it["text"]} for it in items], CHECKS)

    rows, cost = [], 0.0
    for item, (scores, c) in zip(items, results):
        cost += c
        tells = sorted({m.group(0).lower() for m in SLOP.finditer(item["text"])})
        tells += [name for name, v in scores.items() if v >= FLAG_ABOVE]
        rows.append({"id": item["id"], "label": item.get("ai"), "predicted": bool(tells),
                     "tells": tells})

    for r in rows:
        print(f"{'FLAG' if r['predicted'] else 'ok  '} {r['id']:16} {', '.join(r['tells'])}")
    print(f"\nJev cost: ${cost:.5f} for {len(rows)} paragraphs")
    if args.eval:
        print(json.dumps(report(rows), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
