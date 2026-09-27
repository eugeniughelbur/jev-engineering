#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""A safety gate for coding agents, backed by TypeSafe's Jev model.

Reads a proposed tool call on stdin, decides allow / ask / deny, and exits with
the code the harness expects. Designed as a Claude Code PreToolUse hook, but the
decide() function is plain Python and works anywhere.

Order of operations, which is the whole design:
  1. Hard rules  - deterministic denials, no model, single-digit milliseconds.
  2. Fast path   - an allowlist of read-only commands that never calls the model.
  3. Jev         - one request, two questions, answered in parallel.
  4. Thresholds  - your numbers, from your own observe-mode log.

Denials come before the allowlist on purpose. A command name says nothing about
its arguments, so `cat` on the allowlist must not wave through `cat ~/.ssh/id_`.

Fails open. Any error, timeout or missing key falls back to the harness's own
permission prompt, so a network blip never bricks a session.

Modes, set with JEV_GATE_MODE:
    observe  log every decision, change nothing (the default)
    auto     approve what is clearly safe, so its prompt never appears;
             block what is clearly dangerous; ask you about the rest
    guard    block denials, leave every other prompt as it was
    enforce  block denials and anything unsure

Usage:
    echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | ./jev_gate.py
    ./jev_gate.py --explain "git push --force origin main"
    ./jev_gate.py --stats        what auto mode would have done with your log

Exit codes:
    0  allow, or fell back to the normal prompt (auto mode answers in JSON)
    2  deny
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://openrouter.ai/api/v1/systemone")
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")
MODE = os.environ.get("JEV_GATE_MODE", "observe")  # observe | auto | guard | enforce
# Tools auto mode may approve on its own. Bash only by default: file edits
# already have Claude Code's accept-edits mode, and a wrong approval on a
# command is the one worth thinking about.
AUTO_TOOLS = {t.strip() for t in os.environ.get("JEV_AUTO_TOOLS", "Bash").split(",") if t.strip()}
LOG = Path(os.environ.get("JEV_GATE_LOG", Path.home() / ".jev-gate" / "decisions.jsonl"))
TIMEOUT = float(os.environ.get("JEV_GATE_TIMEOUT", "5"))

# The rules live in policy.json, not in this file, so a team can share one copy
# and each person can add to it. Steps 1, 2, 3 and 4 all come from there.
# Run `uv run policy.py show` to see what is in force and where it came from.
sys.path.insert(0, str(Path(__file__).parent))
from policy import load as load_policy  # noqa: E402

POLICY = load_policy()
HARD_DENY = [(r["pattern"], r["reason"]) for r in POLICY.get("hard_deny", [])]
FAST_ALLOW = POLICY.get("fast_path", [])
QUESTIONS = POLICY.get("questions", {})

_T = POLICY.get("thresholds", {})
DENY_ABOVE = float(os.environ.get("JEV_DENY_ABOVE", _T.get("deny_above", 0.90)))
ALLOW_BELOW = float(os.environ.get("JEV_ALLOW_BELOW", _T.get("allow_below", 0.10)))
CONFIDENCE_FLOOR = float(os.environ.get("JEV_CONFIDENCE_FLOOR", _T.get("confidence_floor", 0.45)))


@dataclass
class Decision:
    verdict: str  # allow | ask | deny
    source: str  # fast-path | hard-rule | model | fallback
    reason: str
    destructive: float | None = None
    confidence: float | None = None
    latency_ms: float | None = None
    cost: float | None = None


def hard_rule(command: str) -> Decision | None:
    for pattern, reason in HARD_DENY:
        if re.search(pattern, command):
            return Decision("deny", "hard-rule", reason)
    return None


# Anything that chains, pipes, redirects or substitutes is more than the one
# command the allowlist names. `git status && rm -rf src` starts with
# `git status`, and in auto mode a fast-path allow is an approval.
COMPOUND = re.compile(r"[;&|`<>\n]|\$\(")


# A chain is only as safe as its worst step. `cd repo && git status | head`
# is read-only end to end, so it can skip the model. Anything with quotes,
# substitution or a real redirect is too hard to split safely and goes to Jev.
CHAIN_SPLIT = re.compile(r"&&|\|\||;|\|")
HARMLESS_REDIRECT = re.compile(r"\s*(?:[12]?>\s*/dev/null|2>&1)")
CD = re.compile(r"^\s*cd\s+[\w./~-]+\s*$")


def _one(command: str) -> bool:
    return any(re.search(pattern, command) for pattern in FAST_ALLOW)


def fast_path(command: str) -> Decision | None:
    if not COMPOUND.search(command):
        if _one(command):
            return Decision("allow", "fast-path", "read-only command on the allowlist")
        return None
    if re.search(r"['\"`\n]|\$\(", command):
        return None
    steps = [HARMLESS_REDIRECT.sub("", s).strip() for s in CHAIN_SPLIT.split(command)]
    if not steps or any(not s or re.search(r"[<>&]", s) for s in steps):
        return None
    if all(CD.match(s) or _one(s) for s in steps):
        return Decision("allow", "fast-path", "every step of the chain is read-only")
    return None


def build_state(command: str, tool: str, user_message: str, cwd: str) -> str:
    """Build the state Jev sees.

    Deliberately excludes the model's own reasoning and prior tool output. An
    agent that can write into its own gate's evidence can talk the gate into
    approving it.
    """
    return (
        f"Recent user message: {user_message}\n"
        f"Proposed tool: {tool}\n"
        f"Command: {command}\n"
        f"Working directory: {cwd}"
    )


def ask_jev(state: str, api_key: str, questions: dict | None = None) -> tuple[dict | None, float]:
    body = json.dumps(
        {"model": MODEL, "state": state, "questions": questions or QUESTIONS}
    ).encode()
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read()), (time.perf_counter() - start) * 1000
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        return None, (time.perf_counter() - start) * 1000


def decide(command: str, tool: str = "Bash", user_message: str = "", cwd: str = "") -> Decision:
    # Hard rules run first, always. The fast path is an allowlist of command
    # names, and a command name says nothing about its arguments: `cat` is
    # harmless until it is `cat ~/.ssh/id_ed25519`. Checking the allowlist
    # first would wave that through.
    if found := hard_rule(command):
        return found
    if found := fast_path(command):
        return found

    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        return Decision("ask", "fallback", "no API key set, deferring to the normal prompt")

    payload, latency = ask_jev(build_state(command, tool, user_message, cwd), api_key)
    if payload is None:
        return Decision("ask", "fallback", "model unreachable, deferring to the normal prompt")

    answers = payload["answers"]
    destructive = answers["destructive"]["noul"]
    verdict = answers["verdict"]["choice"]
    confidence = answers["verdict"]["confidence"]
    cost = payload.get("usage", {}).get("cost")

    # A clear destructive reading denies whatever the confidence says. Low
    # confidence can only make the gate more cautious, never less.
    if destructive >= DENY_ABOVE:
        return Decision(
            "deny", "model", f"destructive p={destructive:.2f}", destructive, confidence,
            latency, cost,
        )
    # Low confidence was the one signal that separated successful attacks from
    # clean traffic in testing. It is not enough on its own, which is why the
    # hard rules run first.
    if confidence < CONFIDENCE_FLOOR:
        return Decision(
            "ask", "model", f"low confidence ({confidence:.2f})", destructive, confidence,
            latency, cost,
        )
    if destructive <= ALLOW_BELOW and verdict == "allow":
        return Decision(
            "allow", "model", f"destructive p={destructive:.2f}", destructive, confidence,
            latency, cost,
        )
    return Decision(
        "ask", "model", f"verdict={verdict}, p={destructive:.2f}", destructive, confidence,
        latency, cost,
    )


def log(command: str, decision: Decision, tool: str = "Bash") -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as handle:
            handle.write(
                json.dumps(
                    {
                        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "mode": MODE,
                        "tool": tool,
                        "command": command,
                        **decision.__dict__,
                    }
                )
                + "\n"
            )
    except OSError:
        pass  # logging must never break a session


def last_user_message(transcript_path: str) -> str:
    """Pull the most recent human turn out of the session transcript.

    Claude Code hands the hook a path, not the message. We read only human
    turns: the assistant's own reasoning must never reach the gate, or the
    agent can write its own permission slip.
    """
    if not transcript_path:
        return ""
    try:
        lines = Path(transcript_path).read_text().splitlines()
    except OSError:
        return ""
    for line in reversed(lines[-400:]):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "user":
            continue
        content = entry.get("message", {}).get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()[:2000]
        if isinstance(content, list):
            text = " ".join(
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ).strip()
            if text:
                return text[:2000]
    return ""


def describe(tool: str, tool_input: dict) -> str:
    """One line describing what the tool is about to do, whatever the tool is."""
    if command := tool_input.get("command"):
        return command
    if path := tool_input.get("file_path"):
        return f"{tool} {path}"
    return f"{tool} {json.dumps(tool_input)[:400]}"


def hook_answer(decision: str, reason: str) -> None:
    """Tell Claude Code what to do, in the shape its PreToolUse hooks expect.
    `allow` skips the permission prompt, `deny` blocks and shows the reason."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": f"jev-gate: {reason}",
        }
    }))


def stats() -> int:
    """What auto mode would have done with everything in your log."""
    try:
        rows = [json.loads(line) for line in LOG.read_text().splitlines() if line.strip()]
    except (OSError, ValueError):
        rows = []
    if not rows:
        print(f"No decisions logged yet at {LOG}. Use your agent for a while, then run this again.")
        return 0
    auto_tools = [r for r in rows if r.get("tool", "Bash") in AUTO_TOOLS]
    skip = sum(r["verdict"] == "allow" for r in auto_tools)
    block = sum(r["verdict"] == "deny" for r in rows)
    ask = len(rows) - skip - block
    fallback = sum(r.get("source") == "fallback" for r in rows)
    cost = sum(r.get("cost") or 0 for r in rows)
    lat = sorted(r["latency_ms"] for r in rows if r.get("latency_ms"))
    print(f"{len(rows)} decisions logged, {rows[0]['at'][:10]} to {rows[-1]['at'][:10]}.")
    print(f"  {skip} would have run with no prompt in auto mode")
    print(f"  {block} would have been blocked")
    print(f"  {ask} would still ask you")
    if fallback:
        print(f"  {fallback} had no answer from Jev (no key or no network), so they asked you as normal")
    if lat:
        print(f"  median check {lat[len(lat) // 2]:.0f}ms, total spend ${cost:.4f}")
    print("\nSwitch it on: export JEV_GATE_MODE=auto, then restart Claude Code.")
    return 0


def action_for(decision: Decision, tool: str) -> str:
    """allow, deny or prompt, for the mode in force. Every agent adapter
    below turns this into its own format, so the rules live in one place."""
    if MODE == "auto":
        if decision.verdict == "allow" and tool in AUTO_TOOLS:
            return "allow"
        return "deny" if decision.verdict == "deny" else "prompt"
    if MODE == "guard":
        return "deny" if decision.verdict == "deny" else "prompt"
    if MODE == "enforce":
        return "deny" if decision.verdict in ("deny", "ask") else "prompt"
    return "prompt"  # observe: log only, change nothing


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--stats":
        return stats()
    if len(sys.argv) > 2 and sys.argv[1] == "--explain":
        decision = decide(sys.argv[2])
        print(json.dumps(decision.__dict__, indent=2))
        return 0
    # Claude Code and Codex share one hook format. Cursor has its own.
    agent = sys.argv[sys.argv.index("--agent") + 1] if "--agent" in sys.argv[:-1] else "claude"

    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0  # malformed input, fail open

    if agent == "cursor":
        tool, tool_input = "Bash", {"command": event.get("command", "")}
    else:
        tool = event.get("tool_name", "Bash")
        tool_input = event.get("tool_input", {}) or {}
    command = describe(tool, tool_input)
    if not command:
        return 0

    decision = decide(
        command,
        tool=tool,
        user_message=event.get("user_message") or last_user_message(event.get("transcript_path", "")),
        cwd=event.get("cwd", os.getcwd()),
    )
    log(command, decision, tool)
    action = action_for(decision, tool)

    if agent == "cursor":
        # Cursor reads {"permission": ...}. Printing nothing leaves its own
        # prompt in charge, which is what "prompt" means.
        if action != "prompt":
            print(json.dumps({
                "permission": action,
                "user_message": f"jev-gate: {decision.reason}",
                "agent_message": f"jev-gate: {decision.reason}",
            }))
        return 0

    if action == "allow":
        hook_answer("allow", decision.reason)
    elif action == "deny" and MODE == "auto":
        hook_answer("deny", decision.reason)
    elif action == "deny":
        why = "wants a human" if decision.verdict == "ask" else "blocked"
        print(f"jev-gate {why}: {decision.reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
