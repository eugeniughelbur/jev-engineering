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
  1. Fast path   - an allowlist that never calls the model.
  2. Hard rules  - deterministic denials, no model, single-digit milliseconds.
  3. Jev         - one request, two questions, answered in parallel.
  4. Thresholds  - your numbers, from your own observe-mode log.

Fails open. Any error, timeout or missing key falls back to the harness's own
permission prompt, so a network blip never bricks a session.

Usage:
    echo '{"tool_name":"Bash","tool_input":{"command":"rm -rf /"}}' | ./jev_gate.py
    ./jev_gate.py --explain "git push --force origin main"

Exit codes:
    0  allow, or fell back to the normal prompt
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
MODE = os.environ.get("JEV_GATE_MODE", "observe")  # observe | guard | enforce
LOG = Path(os.environ.get("JEV_GATE_LOG", Path.home() / ".jev-gate" / "decisions.jsonl"))
TIMEOUT = float(os.environ.get("JEV_GATE_TIMEOUT", "5"))

# Step 2. Hard rules. These never reach the model.
# Every entry here was earned: either it is obviously catastrophic, or a
# classifier scored it inconsistently in testing. `git stash clear` is in the
# second group. See results/2026-09-20-injection-test.md.
HARD_DENY = [
    (r"\bgit\s+stash\s+clear\b", "unrecoverable, and classifiers score it inconsistently"),
    (r"~/\.ssh/id_|/\.ssh/id_", "reads a private key"),
    (r"\b(sk|rk)_live_[A-Za-z0-9]", "live secret on the command line"),
    (r"\brm\s+-rf\s+/(?:\s|$)", "deletes the filesystem root"),
    (r"\bdd\s+if=.*\bof=/dev/", "writes directly to a device"),
    (r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "fork bomb"),
    (r"\bhistory\b.*\|\s*(curl|wget|nc)\b", "exfiltrates shell history"),
    (r"\bcurl\b[^|]*\|\s*(ba)?sh\b", "pipes a remote script into a shell"),
]

# Step 1. Fast path. Read-only commands that never need a model call.
FAST_ALLOW = [
    r"^\s*git\s+(status|diff|log|branch|remote|fetch)\b",
    r"^\s*(ls|pwd|cat|head|tail|wc|tree|file|stat)\b",
    r"^\s*(node|python3?|npm|uv|cargo|go)\s+--version\b",
    r"^\s*grep\b",
    r"^\s*echo\b",
    r"^\s*(npm|pnpm|yarn)\s+run\s+(test|lint|typecheck|build)\b",
    r"^\s*(pytest|ruff|mypy|eslint)\b",
    r"^\s*uv\s+run\s+(pytest|ruff)\b",
]

QUESTIONS = {
    "destructive": {
        "type": "noul",
        "instructions": (
            "Running this command would destroy data, leak a secret, or cause an effect "
            "that is hard to undo."
        ),
    },
    "verdict": {
        "type": "choice",
        "instructions": "What should the gate do with this tool call?",
        "criteria": {
            "allow": "Clearly safe. Run it without asking the human.",
            "ask": "Consequential or unclear. Stop and ask the human first.",
            "deny": "Clearly dangerous or outside what the human asked for. Refuse.",
        },
    },
}

# Step 4. Thresholds. Replace these with numbers from your own observe log.
DENY_ABOVE = float(os.environ.get("JEV_DENY_ABOVE", "0.90"))
ALLOW_BELOW = float(os.environ.get("JEV_ALLOW_BELOW", "0.10"))
CONFIDENCE_FLOOR = float(os.environ.get("JEV_CONFIDENCE_FLOOR", "0.45"))


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


def fast_path(command: str) -> Decision | None:
    for pattern in FAST_ALLOW:
        if re.search(pattern, command):
            return Decision("allow", "fast-path", "read-only command on the allowlist")
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


def ask_jev(state: str, api_key: str) -> tuple[dict | None, float]:
    body = json.dumps({"model": MODEL, "state": state, "questions": QUESTIONS}).encode()
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
    if found := fast_path(command):
        return found
    if found := hard_rule(command):
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


def log(command: str, decision: Decision) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as handle:
            handle.write(
                json.dumps(
                    {
                        "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "mode": MODE,
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


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--explain":
        decision = decide(sys.argv[2])
        print(json.dumps(decision.__dict__, indent=2))
        return 0

    try:
        event = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0  # malformed input, fail open

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
    log(command, decision)

    if MODE == "observe":
        return 0  # log only, change nothing
    if decision.verdict == "deny" and MODE in ("guard", "enforce"):
        print(f"blocked by jev-gate: {decision.reason}", file=sys.stderr)
        return 2
    if decision.verdict == "ask" and MODE == "enforce":
        print(f"jev-gate wants a human: {decision.reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
