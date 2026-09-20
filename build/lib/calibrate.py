#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Turn a week of observe-mode logs into your own thresholds.

The defaults in this repo are mine. They came from my commands on my machine.
This reads your decision log and tells you what yours should be, which commands
belong on the fast path, and which belong in a hard rule.

    uv run calibrate.py                 # report and recommend
    uv run calibrate.py --label         # label the ambiguous ones, then measure
    uv run calibrate.py --apply         # write the recommendation to .env

Run it after a week in observe mode. Run it again every month, because your
commands drift and the model gets retrained underneath you.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

LOG = Path(os.environ.get("JEV_GATE_LOG", Path.home() / ".jev-gate" / "decisions.jsonl"))
LABELS = LOG.parent / "labels.json"
CANDIDATES = (0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95)


def load(path: Path) -> list[dict]:
    if not path.exists():
        print(f"no log at {path}", file=sys.stderr)
        print("run in observe mode for a week first, then come back.", file=sys.stderr)
        raise SystemExit(1)
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def normalise(command: str) -> str:
    """Collapse a command to its shape so repeats group together."""
    parts = command.strip().split()
    if not parts:
        return ""
    head = parts[0]
    if head in ("git", "npm", "pnpm", "yarn", "uv", "docker", "kubectl", "aws", "gh") and len(parts) > 1:
        return f"{head} {parts[1]}"
    return head


def section(title: str) -> None:
    print(f"\n{title}")
    print("-" * len(title))


def report_volume(rows: list[dict]) -> list[dict]:
    section("What your log holds")
    print(f"decisions        {len(rows)}")
    if rows:
        print(f"first            {rows[0].get('at', 'unknown')}")
        print(f"last             {rows[-1].get('at', 'unknown')}")

    sources = Counter(r.get("source") for r in rows)
    for name in ("fast-path", "hard-rule", "model", "fallback"):
        count = sources.get(name, 0)
        share = count / len(rows) * 100 if rows else 0
        print(f"{name:16} {count:5}  {share:4.0f}%")

    scored = [r for r in rows if r.get("destructive") is not None]
    if not scored:
        print("\nNo scored decisions yet. The model was never reached.")
        raise SystemExit(0)

    latencies = sorted(r["latency_ms"] for r in scored if r.get("latency_ms"))
    costs = [r["cost"] for r in scored if r.get("cost")]
    if latencies:
        print(f"\nmedian latency   {statistics.median(latencies):.0f}ms")
    if costs:
        days = max(len({r.get("at", "")[:10] for r in rows}), 1)
        print(f"total spend      ${sum(costs):.4f} over {days} day(s)")
        print(f"per day          ${sum(costs) / days:.4f}")
    return scored


def report_interruptions(rows: list[dict]) -> None:
    section("What it would have cost you")
    asks = sum(1 for r in rows if r.get("verdict") == "ask")
    denies = sum(1 for r in rows if r.get("verdict") == "deny")
    total = len(rows)
    print(f"stopped for a human   {asks:5}  {asks / total * 100:4.0f}%")
    print(f"blocked outright      {denies:5}  {denies / total * 100:4.0f}%")
    print(f"ran without asking    {total - asks - denies:5}  {(total - asks - denies) / total * 100:4.0f}%")
    if (asks + denies) / total > 0.25:
        print("\nOver a quarter of your work would have been interrupted.")
        print("Widen the fast path before you touch the thresholds.")


def sweep(scored: list[dict], labels: dict[str, str]) -> None:
    section("Threshold sweep")
    labelled = [r for r in scored if labels.get(r.get("command", "")) in ("safe", "dangerous")]

    if labelled:
        print(f"using {len(labelled)} labelled decisions as ground truth\n")
        print("allow_below  missed dangerous   wrongly stopped safe")
        for floor in CANDIDATES:
            missed = sum(
                1
                for r in labelled
                if labels[r["command"]] == "dangerous" and r["destructive"] <= floor
            )
            stopped = sum(
                1 for r in labelled if labels[r["command"]] == "safe" and r["destructive"] > floor
            )
            dangerous = sum(1 for r in labelled if labels[r["command"]] == "dangerous") or 1
            safe = sum(1 for r in labelled if labels[r["command"]] == "safe") or 1
            print(
                f"{floor:.2f}         {missed:3}/{dangerous:<3} = {missed / dangerous * 100:3.0f}%"
                f"        {stopped:3}/{safe:<3} = {stopped / safe * 100:3.0f}%"
            )
        print("\nPick the lowest row where the first column is zero.")
        print("That is your allow_below. Everything above it gets asked or denied.")
        return

    print("no labels yet, so this shows interruption cost only")
    print("run with --label to get the accuracy columns\n")
    print("allow_below   share of traffic that still gets stopped")
    for floor in CANDIDATES:
        stopped = sum(1 for r in scored if r["destructive"] > floor)
        print(f"{floor:.2f}          {stopped:4}/{len(scored)} = {stopped / len(scored) * 100:3.0f}%")


def confidence_floor(scored: list[dict]) -> None:
    withconf = [r for r in scored if r.get("confidence") is not None]
    if not withconf:
        return
    section("Confidence floor")
    values = sorted(r["confidence"] for r in withconf)
    print(f"median confidence  {statistics.median(values):.3f}")
    print(f"10th percentile    {values[int(len(values) * 0.10)]:.3f}")
    print("\nfloor   extra stops it would add")
    for floor in (0.3, 0.4, 0.5, 0.6, 0.7):
        extra = sum(
            1 for r in withconf if r["confidence"] < floor and r.get("verdict") == "allow"
        )
        print(f"{floor:.1f}     {extra:4}/{len(withconf)} = {extra / len(withconf) * 100:3.0f}%")
    print("\nA low-confidence answer was the signal that separated successful")
    print("attacks from clean traffic in testing. It is a tax, not a free win.")


def suggest_rules(rows: list[dict], scored: list[dict]) -> None:
    section("Rules worth adding")

    # Commands that reach the model often and always come back safe.
    safe_repeats = Counter(
        normalise(r.get("command", ""))
        for r in scored
        if r.get("verdict") == "allow" and r.get("destructive", 1) < 0.05
    )
    promote = [(shape, n) for shape, n in safe_repeats.most_common(8) if n >= 3]
    if promote:
        print("Fast path. These reached the model repeatedly and were never risky.")
        print("Adding them saves the call and the wait.\n")
        for shape, count in promote:
            pattern = re.escape(shape).replace("\\ ", r"\s+")
            print(f'    r"^\\s*{pattern}\\b",   # {count} calls, all clear')

    # Commands that keep getting denied or asked. Those belong in a hard rule.
    blocked = Counter(
        r.get("command", "") for r in rows if r.get("verdict") in ("deny", "ask")
    )
    repeat_blocks = [(cmd, n) for cmd, n in blocked.most_common(8) if n >= 2]
    if repeat_blocks:
        print("\nHard rules. These were stopped more than once.")
        print("If they should always be stopped, name them and skip the model.\n")
        for cmd, count in repeat_blocks:
            print(f"    {count}x  {cmd[:70]}")

    if not promote and not repeat_blocks:
        print("Nothing repeats often enough yet. Keep logging.")


def recommend(scored: list[dict], labels: dict[str, str], apply: bool) -> None:
    section("Your settings")
    labelled = [r for r in scored if labels.get(r.get("command", "")) in ("safe", "dangerous")]

    allow_below = 0.10
    deny_above = 0.90
    if labelled:
        dangerous = [r["destructive"] for r in labelled if labels[r["command"]] == "dangerous"]
        safe = [r["destructive"] for r in labelled if labels[r["command"]] == "safe"]
        if dangerous:
            # Highest floor that still misses nothing dangerous.
            allow_below = max((f for f in CANDIDATES if f < min(dangerous)), default=0.05)
        if safe:
            deny_above = min((f for f in CANDIDATES if f > max(safe)), default=0.90)

    lines = [
        f"JEV_ALLOW_BELOW={allow_below:.2f}",
        f"JEV_DENY_ABOVE={deny_above:.2f}",
        "JEV_CONFIDENCE_FLOOR=0.45",
        "JEV_GATE_MODE=guard",
    ]
    for line in lines:
        print(f"    {line}")
    if not labelled:
        print("\nThese are still the defaults. Label some decisions to earn your own.")

    if apply:
        target = Path(".env")
        existing = target.read_text() if target.exists() else ""
        keep = [
            ln
            for ln in existing.splitlines()
            if not any(ln.startswith(key.split("=")[0]) for key in lines)
        ]
        target.write_text("\n".join(keep + lines) + "\n")
        print(f"\nwritten to {target.resolve()}")


def label_session(scored: list[dict]) -> dict[str, str]:
    labels: dict[str, str] = json.loads(LABELS.read_text()) if LABELS.exists() else {}
    # Label the ambiguous middle first. Those are the ones that move a threshold.
    queue = sorted(
        (r for r in scored if r.get("command") not in labels),
        key=lambda r: abs(r.get("destructive", 0.5) - 0.5),
    )
    if not queue:
        print("everything already labelled")
        return labels

    print(f"{len(queue)} unlabelled. s = safe, d = dangerous, enter = skip, q = stop.\n")
    for row in queue:
        command = row.get("command", "")
        answer = input(f"  [{row.get('destructive', 0):.2f}] {command[:70]}  ")
        if answer.lower() == "q":
            break
        if answer.lower() in ("s", "d"):
            labels[command] = "safe" if answer.lower() == "s" else "dangerous"

    LABELS.parent.mkdir(parents=True, exist_ok=True)
    LABELS.write_text(json.dumps(labels, indent=2))
    print(f"\n{len(labels)} labels saved to {LABELS}")
    return labels


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", action="store_true", help="label decisions to get accuracy")
    parser.add_argument("--apply", action="store_true", help="write the recommendation to .env")
    parser.add_argument("--log", default=str(LOG), help="path to the decision log")
    parser.add_argument("--pool", action="store_true", help="fit on the whole team's pooled log")
    args = parser.parse_args()

    if args.pool:
        from pool import load_pool

        rows = load_pool()
        if not rows:
            print("pool is empty. set JEV_POOL_DIR and have people run pool.py push", file=sys.stderr)
            return 1
        print(f"fitting on {len(rows)} pooled decisions from the team\n")
    else:
        rows = load(Path(args.log))
    scored = report_volume(rows)
    report_interruptions(rows)

    labels: dict[str, str] = json.loads(LABELS.read_text()) if LABELS.exists() else {}
    if args.label:
        labels = label_session(scored)

    sweep(scored, labels)
    confidence_floor(scored)
    suggest_rules(rows, scored)
    recommend(scored, labels, args.apply)

    print("\nRe-run this monthly. Your commands drift and the model gets retrained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
