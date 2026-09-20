#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Question packs, so this is not only a shell-command tool.

A gate is only as good as its questions, and the right questions depend on what
the agent is about to do. Blocking `rm -rf` and blocking a rude email are the
same mechanism with different wording.

Each pack is a JSON file in packs/. Pick one, or copy the closest and edit it.

    uv run packs.py              list the packs
    uv run packs.py show email   print one
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACKS = Path(__file__).parent / "packs"
USER_PACKS = Path.home() / ".jev-gate" / "packs"


def pack_paths() -> dict[str, Path]:
    found: dict[str, Path] = {}
    for folder in (PACKS, USER_PACKS):
        if folder.exists():
            for path in sorted(folder.glob("*.json")):
                found[path.stem] = path  # a user pack of the same name wins
    return found


def pack_names() -> list[str]:
    return sorted(pack_paths())


def load_pack(name: str) -> dict:
    paths = pack_paths()
    if name not in paths:
        raise ValueError(f"no pack called {name!r}. Try: {', '.join(pack_names())}")
    data = json.loads(paths[name].read_text())
    return data["questions"]


def describe(name: str) -> dict:
    return json.loads(pack_paths()[name].read_text())


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "show":
        print(json.dumps(describe(sys.argv[2]), indent=2))
        return 0
    for name in pack_names():
        data = describe(name)
        print(f"{name:12} {data.get('description', '')}")
        for key, question in data["questions"].items():
            kind = question["type"]
            print(f"    {key:14} {kind:7} {question['instructions'][:64]}")
        print()
    print("Copy the closest one into ~/.jev-gate/packs/ and edit it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
