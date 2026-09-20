#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""The three decisions an agent makes constantly, as one call each.

The gate fires on the rare dangerous action. These fire every turn, which is
where the cost and the latency actually live:

    route   which model should handle this turn
    rank    which of these options is the right one
    keep    which parts of this context still earn their place

All three are the same shape underneath: state plus typed questions, one
request, answers in parallel. None of them generates text.

    uv run layer.py route "fix the typo in README" --tiers fast,standard,frontier
    uv run layer.py rank "which file holds the auth logic" --options src/auth.ts,src/db.ts
    uv run layer.py keep transcript.json --budget 0.5
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jev_gate import ask_jev  # noqa: E402

DEFAULT_TIERS = {
    "fast": "Mechanical and clearly scoped. A rename, a typo, a one-line change, a lookup.",
    "standard": "Ordinary implementation work with a known shape.",
    "frontier": "Ambiguous, architectural, or high-stakes. Getting it wrong is expensive.",
}

# Below this, send the turn to the middle tier rather than the top one. A
# published Codex backtest found that falling back to the frontier model on
# every uncertain turn ate about 80% of the savings.
ROUTE_CONFIDENCE_FLOOR = 0.5


def key() -> str:
    found = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not found:
        print("set OPENROUTER_API_KEY or TYPESAFE_API_KEY", file=sys.stderr)
        raise SystemExit(1)
    return found


def route(task: str, tiers: dict[str, str] | None = None) -> dict:
    """Pick which model should handle this turn."""
    tiers = tiers or DEFAULT_TIERS
    questions = {
        "tier": {
            "type": "choice",
            "instructions": "Which tier of model is needed to do this task well?",
            "criteria": tiers,
        }
    }
    payload, latency = ask_jev(task, key(), questions=questions)
    if payload is None:
        middle = list(tiers)[len(tiers) // 2]
        return {"tier": middle, "reason": "model unreachable, defaulted to the middle tier"}

    answer = payload["answers"]["tier"]
    chosen, confidence = answer["choice"], answer.get("confidence", 0.0)
    names = list(tiers)
    reason = "chosen"
    if confidence < ROUTE_CONFIDENCE_FLOOR and chosen == names[0]:
        # Uncertain and cheap is the bad combination. Step up one, not to the top.
        chosen = names[min(1, len(names) - 1)]
        reason = f"low confidence ({confidence:.2f}), stepped up one tier"
    return {
        "tier": chosen,
        "confidence": confidence,
        "probabilities": answer.get("probabilities", {}),
        "reason": reason,
        "latency_ms": round(latency),
        "cost": payload.get("usage", {}).get("cost"),
    }


def rank(options: list[str], criterion: str, context: str = "") -> dict:
    """Order options against one criterion, in a single request."""
    if not options:
        return {"error": "send at least one option"}
    if len(options) > 255:
        return {"error": f"255 options maximum, got {len(options)}"}

    questions = {
        "best": {
            "type": "choice",
            "instructions": criterion,
            "criteria": {str(i): option for i, option in enumerate(options)},
        }
    }
    payload, latency = ask_jev(context or criterion, key(), questions=questions)
    if payload is None:
        return {"error": "model unreachable"}

    answer = payload["answers"]["best"]
    probabilities = answer.get("probabilities", {})
    ordered = sorted(
        ((options[int(i)], p) for i, p in probabilities.items()), key=lambda x: -x[1]
    )
    return {
        "winner": options[int(answer["choice"])],
        "confidence": answer.get("confidence"),
        "ranked": [{"option": o, "probability": p} for o, p in ordered],
        "latency_ms": round(latency),
        "cost": payload.get("usage", {}).get("cost"),
    }


def keep(items: list[str], goal: str, budget: float = 0.5) -> dict:
    """Decide which pieces of context still earn their place.

    One request, one question per item, answered in parallel. Nothing is
    rewritten or summarised: an item is kept verbatim or dropped, because a
    summary silently loses the exact path or error you needed later.

    budget is the share of items to keep when everything scores similarly.
    """
    if not items:
        return {"keep": [], "drop": []}
    if len(items) > 200:
        return {"error": f"200 items maximum per request, got {len(items)}. Chunk it."}

    questions = {
        str(i): {
            "type": "noul",
            "instructions": (
                f"This item is still needed to finish the task, and re-deriving it later "
                f"would cost real work. Item: {item[:400]}"
            ),
        }
        for i, item in enumerate(items)
    }
    payload, latency = ask_jev(f"The task: {goal}", key(), questions=questions)
    if payload is None:
        return {"error": "model unreachable, keep everything"}

    scored = sorted(
        ((items[int(i)], a["noul"]) for i, a in payload["answers"].items()),
        key=lambda x: -x[1],
    )
    cutoff = max(1, round(len(items) * budget))
    return {
        "keep": [{"item": it, "score": s} for it, s in scored[:cutoff]],
        "drop": [{"item": it, "score": s} for it, s in scored[cutoff:]],
        "kept": cutoff,
        "of": len(items),
        "latency_ms": round(latency),
        "cost": payload.get("usage", {}).get("cost"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)

    r = sub.add_parser("route", help="pick a model tier for a turn")
    r.add_argument("task")
    r.add_argument("--tiers", help="comma-separated tier names, using the built-in descriptions")

    k = sub.add_parser("rank", help="order options against one criterion")
    k.add_argument("criterion")
    k.add_argument("--options", required=True, help="comma-separated")
    k.add_argument("--context", default="")

    c = sub.add_parser("keep", help="decide which context items still earn their place")
    c.add_argument("file", help="a JSON array of strings, or - for stdin")
    c.add_argument("--goal", required=True)
    c.add_argument("--budget", type=float, default=0.5)

    args = parser.parse_args()

    if args.action == "route":
        tiers = None
        if args.tiers:
            wanted = [t.strip() for t in args.tiers.split(",")]
            tiers = {t: DEFAULT_TIERS.get(t, f"Use the {t} tier.") for t in wanted}
        print(json.dumps(route(args.task, tiers), indent=2))
    elif args.action == "rank":
        options = [o.strip() for o in args.options.split(",") if o.strip()]
        print(json.dumps(rank(options, args.criterion, args.context), indent=2))
    else:
        raw = sys.stdin.read() if args.file == "-" else Path(args.file).read_text()
        print(json.dumps(keep(json.loads(raw), args.goal, args.budget), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
