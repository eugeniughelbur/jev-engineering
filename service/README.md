# Running it as a background service

The Claude Code plugin guards one agent. This guards everything else: n8n workflows, cron jobs, a deploy step, a bot about to send a message. Same four steps, same log, one place to change the rules.

## Start it

```bash
export OPENROUTER_API_KEY=sk-or-...
./service/install.sh
```

That writes a launchd job that starts at login and restarts if it dies. Check it:

```bash
curl -s localhost:8787/health
```

Remove it with `./service/install.sh uninstall`.

To run it in the foreground instead, `uv run serve.py`.

## Ask it something

```bash
curl -s localhost:8787/check -H 'Content-Type: application/json' -d '{
  "command": "aws s3 rm s3://prod-backups --recursive",
  "user_message": "clean up old build artifacts"
}'
```

```json
{
  "verdict": "deny",
  "source": "model",
  "reason": "destructive p=0.92",
  "destructive": 0.92,
  "confidence": 0.62,
  "latency_ms": 658,
  "cost": 0.0000176,
  "mode": "observe",
  "proceed": true,
  "advisory": true,
  "note": "observe mode: the gate would have said deny, but is not enforcing."
}
```

Read `verdict` if you want the judgement. Read `proceed` if you only want a boolean. In observe mode `proceed` is always true and `advisory` tells you the gate disagreed, so nothing changes behaviour until you set `JEV_GATE_MODE=guard`.

`user_message` is what the human asked for. Send it. Without it the gate is judging an action with no idea whether anyone wanted it.

## Endpoints

| Route | What it does |
|---|---|
| `POST /check` | The decision. Send `command`, optionally `tool`, `user_message`, `cwd`. |
| `GET /health` | Alive, current mode, log path. |
| `GET /stats` | Decision counts, verdict split, median latency, total spend. |

## Wiring it in

**A shell script, before anything destructive**

```bash
verdict=$(curl -s localhost:8787/check -d "{\"command\":\"$CMD\"}" | jq -r .verdict)
[ "$verdict" = "deny" ] && { echo "blocked by jev-gate"; exit 1; }
```

**n8n.** An HTTP Request node pointed at `/check`, then an IF node on `verdict`. That is the whole integration.

**A GitHub Action, before a deploy.** Run the check on the deploy command and fail the job on `deny`. The service has to be reachable from the runner, so this suits a self-hosted runner, not a cloud one.

**A bot, before it sends.** Pass the draft message as `command` and ask your own question instead of the default one. Edit `QUESTIONS` in `jev_gate.py` to something like "this message would embarrass the sender if it were public".

## Locking it down

It binds to `127.0.0.1` and refuses to start on any other interface. A service that decides what your automation may do should not be reachable from outside the machine. If you need it elsewhere, tunnel to it.

Set `JEV_GATE_TOKEN` to require `Authorization: Bearer <token>` on `/check` and `/stats`. Worth doing on a shared machine, where any local process can otherwise ask.

The launchd plist holds your API key, so `install.sh` writes it `chmod 600`.

## Cost

Every request that reaches the model costs about $0.0000189. Fast-path and hard-rule decisions cost nothing and never leave the machine. Check `GET /stats` for your running total.
