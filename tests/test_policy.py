#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Checks that need no key and no network. Safe to run in CI on every change.

    uv run tests/test_policy.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from packs import describe, pack_names  # noqa: E402
from policy import EMBEDDED, load, validate  # noqa: E402
from pool import redact  # noqa: E402

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'pass' if ok else 'FAIL'}  {name}")
    if not ok:
        failures.append(f"{name}: {detail}")


def main() -> int:
    # The file and the embedded copy must not drift. A silent difference
    # changes what the gate blocks depending on how it was installed.
    shipped = json.loads((ROOT / "policy.json").read_text())
    for key in ("thresholds", "fast_path", "hard_deny", "questions"):
        check(
            f"policy.json {key} matches the embedded default",
            shipped.get(key) == EMBEDDED.get(key),
            "edit both, or neither",
        )

    check("shipped policy is valid", not validate(shipped), "; ".join(validate(shipped)))
    check("merged policy is valid", not validate(load()), "; ".join(validate(load())))

    # A hard rule that does not compile never fires, and fails silently.
    for rule in shipped["hard_deny"]:
        try:
            re.compile(rule["pattern"])
            ok, detail = True, ""
        except re.error as exc:
            ok, detail = False, str(exc)
        check(f"hard rule compiles: {rule['pattern'][:38]}", ok, detail)

    # Every pack needs a verdict question, or nothing can act on the answer.
    for name in pack_names():
        data = describe(name)
        check(f"pack '{name}' has a verdict question", "verdict" in data["questions"])
        check(f"pack '{name}' has a description", bool(data.get("description")))

    # Redaction is the promise the pool makes. Test it directly.
    secrets = [
        ("curl -H 'Authorization: Bearer sk_live_51H8xQ2abcdef' x", "sk_live"),
        ("deploy --token ghp_abcdefghijklmnop1234", "ghp_"),
        ("aws configure set key AKIAIOSFODNN7EXAMPLE", "AKIA"),
        ("mail bob@example.com", "@example.com"),
    ]
    for command, leak in secrets:
        check(f"redacted: {leak}", leak not in redact(command), redact(command))

    if failures:
        print(f"\n{len(failures)} failure(s):")
        for line in failures:
            print(f"  {line}")
        return 1
    print("\nall checks pass, no key and no network used")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
