#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""One set of rules a team shares, and the personal layer on top.

Three layers, merged in this order:

  1. the shipped default, policy.json in this repo
  2. the team policy, pulled from JEV_POLICY_URL and cached locally
  3. your personal overrides, ~/.jev-gate/policy.local.json

Rules add up. Thresholds only tighten. You can make your own copy stricter than
the team's and you cannot make it looser, because a shared rule that any member
can quietly switch off is not a shared rule.

    uv run policy.py pull        fetch the team policy and cache it
    uv run policy.py show        print what is in force and where each part came from
    uv run policy.py check       validate every regex compiles
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("JEV_GATE_HOME", Path.home() / ".jev-gate"))
TEAM_CACHE = HOME / "team-policy.json"
LOCAL = HOME / "policy.local.json"
SHIPPED = Path(__file__).parent / "policy.json"
POLICY_URL = os.environ.get("JEV_POLICY_URL", "")

# Thresholds where "stricter" means a smaller number, and where it means larger.
TIGHTEN_DOWN = ("deny_above", "allow_below")
TIGHTEN_UP = ("confidence_floor",)


# Installed from PyPI there is no policy.json next to this module, so the
# baseline lives here too. tests/test_policy.py asserts the two stay identical,
# because a silent drift between them would change what the gate blocks.
EMBEDDED: dict = {
    "version": "1.0.0",
    "name": "default",
    "thresholds": {"deny_above": 0.9, "allow_below": 0.1, "confidence_floor": 0.45},
    "fast_path": [
        r"^\s*git\s+(status|diff|log|branch|remote|fetch)\b",
        r"^\s*(ls|pwd|cat|head|tail|wc|tree|file|stat)\b",
        r"^\s*(node|python3?|npm|uv|cargo|go)\s+--version\b",
        r"^\s*grep\b",
        r"^\s*echo\b",
        r"^\s*(npm|pnpm|yarn)\s+run\s+(test|lint|typecheck|build)\b",
        r"^\s*(pytest|ruff|mypy|eslint)\b",
        r"^\s*uv\s+run\s+(pytest|ruff)\b",
    ],
    "hard_deny": [
        {"pattern": r"\bgit\s+stash\s+clear\b", "reason": "unrecoverable, and classifiers score it inconsistently"},
        {"pattern": r"~/\.ssh/id_|/\.ssh/id_", "reason": "reads a private key"},
        {"pattern": r"\b(sk|rk)_live_[A-Za-z0-9]", "reason": "live secret on the command line"},
        {"pattern": r"\brm\s+-rf\s+/(?:\s|$)", "reason": "deletes the filesystem root"},
        {"pattern": r"\bdd\s+if=.*\bof=/dev/", "reason": "writes directly to a device"},
        {"pattern": r":\(\)\s*\{\s*:\|:&\s*\}\s*;:", "reason": "fork bomb"},
        {"pattern": r"\bhistory\b.*\|\s*(curl|wget|nc)\b", "reason": "exfiltrates shell history"},
        {"pattern": r"\bcurl\b[^|]*\|\s*(ba)?sh\b", "reason": "pipes a remote script into a shell"},
    ],
    "questions": {
        "destructive": {
            "type": "noul",
            "instructions": "Running this command would destroy data, leak a secret, or cause an effect that is hard to undo.",
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
    },
}


def read(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def merge(base: dict, layer: dict, source: str, trace: list[str]) -> dict:
    """Add rules, tighten thresholds, never loosen."""
    out = json.loads(json.dumps(base))

    for key in ("fast_path",):
        added = [r for r in layer.get(key, []) if r not in out.get(key, [])]
        if added:
            out.setdefault(key, []).extend(added)
            trace.append(f"{source}: +{len(added)} fast-path rule(s)")

    seen = {r["pattern"] for r in out.get("hard_deny", [])}
    added_deny = [r for r in layer.get("hard_deny", []) if r.get("pattern") not in seen]
    if added_deny:
        out.setdefault("hard_deny", []).extend(added_deny)
        trace.append(f"{source}: +{len(added_deny)} hard rule(s)")

    if questions := layer.get("questions"):
        out["questions"] = {**out.get("questions", {}), **questions}
        trace.append(f"{source}: questions replaced")

    for key, value in (layer.get("thresholds") or {}).items():
        current = out.setdefault("thresholds", {}).get(key)
        if current is None:
            out["thresholds"][key] = value
            continue
        if key in TIGHTEN_DOWN and value < current:
            out["thresholds"][key] = value
            trace.append(f"{source}: {key} tightened {current} -> {value}")
        elif key in TIGHTEN_UP and value > current:
            out["thresholds"][key] = value
            trace.append(f"{source}: {key} tightened {current} -> {value}")
        elif value != current:
            trace.append(f"{source}: {key}={value} ignored, it would loosen {current}")
    return out


def load(with_trace: bool = False) -> dict | tuple[dict, list[str]]:
    trace: list[str] = []
    policy = read(SHIPPED) or json.loads(json.dumps(EMBEDDED))
    trace.append(f"shipped default v{policy.get('version', '?')}")

    if team := read(TEAM_CACHE):
        policy = merge(policy, team, f"team '{team.get('name', 'team')}'", trace)
        age_days = (time.time() - TEAM_CACHE.stat().st_mtime) / 86400
        if age_days > 30:
            trace.append(f"team policy is {age_days:.0f} days old, run policy.py pull")

    if local := read(LOCAL):
        policy = merge(policy, local, "yours", trace)

    return (policy, trace) if with_trace else policy


def pull() -> int:
    if not POLICY_URL:
        print("set JEV_POLICY_URL to your team's policy.json first", file=sys.stderr)
        print("example: https://raw.githubusercontent.com/you/team-policy/main/policy.json", file=sys.stderr)
        return 1
    try:
        with urllib.request.urlopen(POLICY_URL, timeout=20) as response:
            fetched = json.loads(response.read())
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"could not fetch: {exc}", file=sys.stderr)
        print("keeping the cached copy" if TEAM_CACHE.exists() else "no cached copy to fall back on", file=sys.stderr)
        return 1

    problems = validate(fetched)
    if problems:
        print("refusing to cache, the fetched policy is broken:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1

    HOME.mkdir(parents=True, exist_ok=True)
    TEAM_CACHE.write_text(json.dumps(fetched, indent=2))
    print(f"pulled '{fetched.get('name', 'team')}' v{fetched.get('version', '?')} to {TEAM_CACHE}")
    print(f"{len(fetched.get('hard_deny', []))} hard rule(s), {len(fetched.get('fast_path', []))} fast-path rule(s)")
    return 0


def validate(policy: dict) -> list[str]:
    problems = []
    for pattern in policy.get("fast_path", []):
        try:
            re.compile(pattern)
        except re.error as exc:
            problems.append(f"fast_path {pattern!r}: {exc}")
    for rule in policy.get("hard_deny", []):
        if "pattern" not in rule or "reason" not in rule:
            problems.append(f"hard_deny entry missing pattern or reason: {rule}")
            continue
        try:
            re.compile(rule["pattern"])
        except re.error as exc:
            problems.append(f"hard_deny {rule['pattern']!r}: {exc}")
    for key, value in (policy.get("thresholds") or {}).items():
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            problems.append(f"threshold {key}={value} must be between 0 and 1")
    return problems


def show() -> int:
    policy, trace = load(with_trace=True)
    print("Where it came from")
    print("------------------")
    for line in trace:
        print(f"  {line}")

    print("\nThresholds in force")
    print("-------------------")
    for key, value in (policy.get("thresholds") or {}).items():
        env = os.environ.get(f"JEV_{key.upper()}")
        note = f"   (environment overrides this to {env})" if env else ""
        print(f"  {key:18} {value}{note}")

    print(f"\nHard rules ({len(policy.get('hard_deny', []))})")
    print("-----------")
    for rule in policy.get("hard_deny", []):
        print(f"  {rule['pattern'][:44]:46} {rule['reason']}")

    print(f"\nFast path ({len(policy.get('fast_path', []))}) skips the model entirely")
    print("----------")
    for pattern in policy.get("fast_path", []):
        print(f"  {pattern}")

    if problems := validate(policy):
        print("\nProblems")
        print("--------")
        for line in problems:
            print(f"  {line}")
        return 1
    return 0


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else "show"
    if action == "pull":
        return pull()
    if action == "check":
        problems = validate(load())
        print("\n".join(problems) if problems else "policy is valid")
        return 1 if problems else 0
    if action == "show":
        return show()
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
