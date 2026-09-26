"""Split one fuzzy question into small checks, and ask Jev all of them at once.

Every use case here has the same shape. "Is this email urgent?" or "does this
read like AI?" is too vague to ask directly. So it becomes a few yes/no checks
with plain definitions. Jev scores each one as a probability, in parallel, and
ordinary code combines the scores into a decision you can explain.

    from jevchecks import Check, run
    results = run(items, [Check("human", "A real person wrote this message.")])

Standard library only. One retry on a busy or failed request, and answers
cached on disk by exact request, so re-running an eval costs nothing.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

ENDPOINT = os.environ.get("JEV_ENDPOINT", "https://openrouter.ai/api/v1/systemone")
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")
TIMEOUT_S = float(os.environ.get("JEV_TIMEOUT", "20"))
PARALLEL = int(os.environ.get("JEV_PARALLEL", "8"))
CACHE_DIR = Path(os.environ.get("JEV_CACHE_DIR", Path.home() / ".cache" / "jevchecks"))
CACHE_ON = os.environ.get("JEV_CACHE", "1") != "0"


@dataclass(frozen=True)
class Check:
    name: str
    instructions: str


def key() -> str:
    found = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("TYPESAFE_API_KEY")
    if not found:
        raise SystemExit("set OPENROUTER_API_KEY or TYPESAFE_API_KEY")
    return found


def call(state: object, questions: dict) -> dict:
    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
    for attempt in (1, 2):
        request = urllib.request.Request(
            ENDPOINT, data=body, method="POST",
            headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as exc:
            if attempt == 2 or not (exc.code == 429 or exc.code >= 500):
                raise
            time.sleep(1.0)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(1.0)
    raise RuntimeError("unreachable")


def ask(state: object, checks: list[Check]) -> tuple[dict[str, float], float]:
    """Score every check against one item. Returns probabilities and cost."""
    questions = {c.name: {"type": "noul", "instructions": c.instructions} for c in checks}
    raw = json.dumps({"m": MODEL, "s": state, "q": questions}, sort_keys=True)
    path = CACHE_DIR / f"{hashlib.sha256(raw.encode()).hexdigest()}.json"
    if CACHE_ON and path.exists():
        try:
            return json.loads(path.read_text()), 0.0
        except ValueError:
            pass
    payload = call(state, questions)
    scores = {name: float(a["noul"]) for name, a in payload["answers"].items()}
    if CACHE_ON:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(scores))
    return scores, float(payload.get("usage", {}).get("cost") or 0.0)


def run(items: list[object], checks: list[Check]) -> list[tuple[dict[str, float], float]]:
    """Score every item, in parallel, keeping the input order."""
    with ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        return list(pool.map(lambda item: ask(item, checks), items))


def report(rows: list[dict], label: str = "label", predicted: str = "predicted") -> dict:
    """Agreement with hand labels, with the disagreements listed by name."""
    tp = sum(r[label] and r[predicted] for r in rows)
    fp = sum(not r[label] and r[predicted] for r in rows)
    fn = sum(r[label] and not r[predicted] for r in rows)
    tn = len(rows) - tp - fp - fn
    return {
        "items": len(rows),
        "agree": tp + tn,
        "precision": round(tp / (tp + fp), 2) if tp + fp else None,
        "recall": round(tp / (tp + fn), 2) if tp + fn else None,
        "missed": [r["id"] for r in rows if r[label] and not r[predicted]],
        "false_alarms": [r["id"] for r in rows if not r[label] and r[predicted]],
    }
