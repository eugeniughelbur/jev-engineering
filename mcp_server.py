#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp"]
# ///
"""Expose the gate over MCP, so any MCP client can ask it.

The Claude Code hook runs whether the model likes it or not. This is the other
shape: the agent decides to ask. Use the hook when you need to force a check,
and this when you want the agent to be able to seek a second opinion.

Cursor, in .cursor/mcp.json:

    { "mcpServers": { "jev-gate": {
        "command": "uv",
        "args": ["run", "--directory", "/abs/path/to/jev-gate", "mcp_server.py"],
        "env": { "OPENROUTER_API_KEY": "sk-or-..." } } } }

Codex:

    codex mcp add jev-gate --env OPENROUTER_API_KEY=sk-or-... \
      -- uv run --directory /abs/path/to/jev-gate mcp_server.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Literal

try:  # mcp 2.x
    from mcp.server.mcpserver import MCPServer as _Server
except ModuleNotFoundError:  # mcp 1.x, where it was called FastMCP
    from mcp.server.fastmcp import FastMCP as _Server

sys.path.insert(0, str(Path(__file__).parent))
from jev_gate import LOG, MODE, ask_jev, decide, log  # noqa: E402
from packs import load_pack, pack_names  # noqa: E402

mcp = _Server("jev-gate")


def key() -> str:
    found = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not found:
        raise RuntimeError("set OPENROUTER_API_KEY or TYPESAFE_API_KEY")
    return found


@mcp.tool()
def check_action(action: str, user_asked_for: str = "", pack: str = "shell") -> str:
    """Judge whether an action is safe to take, before taking it.

    Returns allow, ask or deny with a probability, a confidence and a reason.
    Call this before anything destructive, irreversible, or outside what the
    user asked for.

    action: the exact thing about to happen, such as a shell command, an email
        body, or a description of the API call.
    user_asked_for: what the human actually requested, verbatim. Send it. A
        judgement about authorization is worthless without it.
    pack: which question set to use. One of: {packs}.
    """
    questions = load_pack(pack)
    if pack == "shell":
        result = decide(action, user_message=user_asked_for)
        log(action, result)
        body = dict(result.__dict__)
    else:
        state = f"What the human asked for: {user_asked_for}\nProposed action: {action}"
        payload, latency = ask_jev(state, key(), questions=questions)
        if payload is None:
            return json.dumps({"verdict": "ask", "reason": "model unreachable, ask the human"})
        answers = payload["answers"]
        body = {
            "answers": {k: v.get("noul", v.get("choice", v.get("score"))) for k, v in answers.items()},
            "confidence": next(
                (v["confidence"] for v in answers.values() if "confidence" in v), None
            ),
            "latency_ms": round(latency),
            "cost": payload.get("usage", {}).get("cost"),
        }
    body["mode"] = MODE
    body["pack"] = pack
    return json.dumps(body, indent=2)


check_action.__doc__ = (check_action.__doc__ or "").format(packs=", ".join(pack_names()))


@mcp.tool()
def rank_options(options: list[str], criterion: str, context: str = "") -> str:
    """Rank a list of options against one criterion, in a single call.

    Cheaper and faster than asking a chat model to sort them, and it returns a
    probability per option rather than an opinion. Good for choosing a file,
    a tool, a model tier, or reordering search results.

    options: up to 255 choices.
    criterion: what makes one option better, as a plain statement.
    context: whatever the options should be judged against.
    """
    if not options:
        return json.dumps({"error": "send at least one option"})
    if len(options) > 255:
        return json.dumps({"error": f"255 options maximum, got {len(options)}"})

    questions = {
        "best": {
            "type": "choice",
            "instructions": criterion,
            "criteria": {str(i): option for i, option in enumerate(options)},
        }
    }
    payload, latency = ask_jev(context or criterion, key(), questions=questions)
    if payload is None:
        return json.dumps({"error": "model unreachable"})

    answer = payload["answers"]["best"]
    probabilities = answer.get("probabilities", {})
    ranked = sorted(
        ((options[int(i)], p) for i, p in probabilities.items()), key=lambda x: -x[1]
    )
    return json.dumps(
        {
            "winner": options[int(answer["choice"])],
            "confidence": answer.get("confidence"),
            "ranked": [{"option": o, "probability": p} for o, p in ranked],
            "latency_ms": round(latency),
            "cost": payload.get("usage", {}).get("cost"),
        },
        indent=2,
    )


@mcp.tool()
def gate_stats() -> str:
    """What the gate has decided so far: counts, verdict split and spend."""
    if not LOG.exists():
        return json.dumps({"decisions": 0, "log": str(LOG)})
    rows = []
    for line in LOG.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    verdicts: dict[str, int] = {}
    for row in rows:
        verdicts[row.get("verdict", "?")] = verdicts.get(row.get("verdict", "?"), 0) + 1
    return json.dumps(
        {
            "decisions": len(rows),
            "verdicts": verdicts,
            "total_cost": round(sum(r.get("cost") or 0 for r in rows), 6),
            "mode": MODE,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
