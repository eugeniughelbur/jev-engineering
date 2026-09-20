#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Run the gate as a small always-on service, so anything can ask it.

The Claude Code hook guards one agent. This guards everything else: n8n
workflows, cron jobs, a deploy step, a bot about to send a message. Same four
steps, same log, one place to change the rules.

    uv run serve.py                 # http://127.0.0.1:8787
    curl -s localhost:8787/check -d '{"command":"rm -rf /"}'

Binds to loopback only. It never listens on a public interface, because a
service that decides what your automation may do should not be reachable from
outside the machine. Set JEV_GATE_TOKEN to require a shared secret as well.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from jev_gate import LOG, MODE, decide, log  # noqa: E402

HOST = os.environ.get("JEV_GATE_HOST", "127.0.0.1")
PORT = int(os.environ.get("JEV_GATE_PORT", "8787"))
TOKEN = os.environ.get("JEV_GATE_TOKEN", "")
MAX_BODY = 64 * 1024


class Handler(BaseHTTPRequestHandler):
    server_version = "jev-gate"

    def log_message(self, fmt: str, *args) -> None:  # quieter than the default
        sys.stderr.write(f"{self.address_string()} {fmt % args}\n")

    def send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorised(self) -> bool:
        if not TOKEN:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {TOKEN}"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self.send_json(200, {"ok": True, "mode": MODE, "log": str(LOG)})
            return
        if self.path == "/stats":
            if not self.authorised():
                self.send_json(401, {"error": "unauthorised"})
                return
            self.send_json(200, stats())
            return
        self.send_json(404, {"error": "try /health, /stats or POST /check"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/check":
            self.send_json(404, {"error": "try POST /check"})
            return
        if not self.authorised():
            self.send_json(401, {"error": "unauthorised"})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self.send_json(413, {"error": "body too large"})
            return
        try:
            payload = json.loads(self.rfile.read(length) or "{}")
        except ValueError:
            self.send_json(400, {"error": "body must be JSON"})
            return

        command = payload.get("command") or payload.get("action")
        if not command:
            self.send_json(400, {"error": "send a command or an action"})
            return

        decision = decide(
            str(command),
            tool=payload.get("tool", "Bash"),
            user_message=payload.get("user_message", ""),
            cwd=payload.get("cwd", ""),
        )
        log(str(command), decision)

        body = dict(decision.__dict__)
        body["mode"] = MODE
        # Callers that only want a boolean can read this and ignore the rest.
        body["proceed"] = decision.verdict == "allow" or MODE == "observe"
        if MODE == "observe" and decision.verdict != "allow":
            # Loud, because a caller reading only `proceed` would otherwise
            # believe the gate approved something it wanted to stop.
            body["advisory"] = True
            body["note"] = (
                f"observe mode: the gate would have said {decision.verdict}, "
                "but is not enforcing. Set JEV_GATE_MODE=guard to act on it."
            )
        self.send_json(200, body)


def stats() -> dict:
    if not LOG.exists():
        return {"decisions": 0}
    rows = []
    for line in LOG.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    if not rows:
        return {"decisions": 0}
    latencies = [r["latency_ms"] for r in rows if r.get("latency_ms")]
    return {
        "decisions": len(rows),
        "first": rows[0].get("at"),
        "last": rows[-1].get("at"),
        "verdicts": dict(Counter(r.get("verdict") for r in rows)),
        "sources": dict(Counter(r.get("source") for r in rows)),
        "median_latency_ms": round(statistics.median(latencies)) if latencies else None,
        "total_cost": round(sum(r.get("cost") or 0 for r in rows), 6),
    }


def main() -> int:
    if HOST not in ("127.0.0.1", "localhost", "::1"):
        print(f"refusing to bind {HOST}. This service decides what your automation", file=sys.stderr)
        print("may do. Keep it on loopback and reach it through a tunnel if you", file=sys.stderr)
        print("need it from elsewhere.", file=sys.stderr)
        return 2

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"jev-gate listening on http://{HOST}:{PORT}  mode={MODE}")
    print(f"log {LOG}")
    if not TOKEN:
        print("no JEV_GATE_TOKEN set, so any local process can ask")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
