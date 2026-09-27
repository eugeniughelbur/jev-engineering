#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""How many permission prompts would auto mode remove? Replay your own history.

Reads the Bash commands Claude Code actually ran for you, from its session
transcripts, and asks the gate about each one, exactly as auto mode would.

    uv run bench_prompts.py ~/.claude/projects/-Users-you-Projects-*
    uv run bench_prompts.py DIR... --out results/prompts.json

Commands are redacted with pool.py before they are sent anywhere, and the
output holds only totals and first words, never a full command. Costs about
$0.00002 per command that reaches Jev.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jev_gate import decide  # noqa: E402
from pool import redact  # noqa: E402


def commands(dirs: list[str]) -> list[str]:
    found = []
    for d in dirs:
        for path in sorted(glob.glob(os.path.join(d, "*.jsonl"))):
            with open(path, errors="ignore") as handle:
                for line in handle:
                    try:
                        event = json.loads(line)
                    except ValueError:
                        continue
                    if event.get("type") != "assistant":
                        continue
                    for block in event.get("message", {}).get("content") or []:
                        is_bash = isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Bash"
                        if is_bash and (cmd := (block.get("input") or {}).get("command")):
                            found.append(cmd)
    return found


def first_word(cmd: str) -> str:
    words = [w for w in cmd.replace("\n", " ").split() if "=" not in w or w.startswith("-")]
    head = words[0] if words else "?"
    if head in ("git", "npm", "uv", "gh", "docker", "python3", "npx", "pnpm", "yarn") and len(words) > 1:
        return f"{head} {words[1]}"
    return head.rsplit("/", 1)[-1]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("dirs", nargs="+", help="Claude Code transcript folders")
    p.add_argument("--out", type=Path, help="write the totals as JSON here")
    p.add_argument("--workers", type=int, default=8)
    args = p.parse_args()

    raw = commands(args.dirs)
    if not raw:
        print("no Bash commands found in those folders")
        return 1
    cmds = [redact(c) for c in raw]
    start = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        decisions = list(pool.map(decide, cmds))

    by = collections.Counter(d.verdict for d in decisions)
    src = collections.Counter(f"{d.verdict}/{d.source}" for d in decisions)
    asks = collections.Counter(first_word(c) for c, d in zip(cmds, decisions) if d.verdict == "ask")
    denies = collections.Counter(d.reason for d in decisions if d.verdict == "deny")
    lat = sorted(d.latency_ms for d in decisions if d.latency_ms)
    cost = sum(d.cost or 0 for d in decisions)
    fallback = sum(d.source == "fallback" for d in decisions)
    n = len(decisions)
    result = {
        "commands": n,
        "run_on": time.strftime("%Y-%m-%d"),
        "auto_approved": by["allow"],
        "blocked": by["deny"],
        "still_ask": by["ask"],
        "no_answer_fallback": fallback,
        "prompts_removed_pct": round(100 * by["allow"] / n, 1),
        "by_source": dict(src.most_common()),
        "still_ask_top_first_words": dict(asks.most_common(12)),
        "block_reasons": dict(denies.most_common(10)),
        "median_ms": round(lat[len(lat) // 2]) if lat else None,
        "model_calls": len(lat),
        "cost_usd": round(cost, 4),
        "wall_seconds": round(time.time() - start),
    }
    print(json.dumps(result, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
