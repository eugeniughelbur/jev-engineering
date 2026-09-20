---
description: Show whether the gate is running, which mode it is in, and what it has decided so far
---

Report the current state of jev-gate. Do not change anything.

1. Check the mode. Read `JEV_GATE_MODE` from the environment. If unset, the mode is `observe`, which logs and blocks nothing.

2. Check the key. Confirm `OPENROUTER_API_KEY` or `TYPESAFE_API_KEY` is set. Do not print any part of the key itself. If neither is set, say so plainly: the gate is falling back to the normal permission prompt on every call.

3. Read the log at `JEV_GATE_LOG`, or `~/.jev-gate/decisions.jsonl` if unset. Report:
   - how many decisions it holds and the date range
   - the split across fast-path, hard-rule, model and fallback
   - the split across allow, ask and deny
   - median latency and total spend

4. Run one live check so the user can see it working:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/jev_gate.py" --explain "git push --force origin main"
```

5. Close with the one thing to do next:
   - fewer than 7 days of log: keep running in observe mode
   - 7 days or more and still in observe: run `/jev-calibrate`
   - no key set: point at `.env.example`

Keep the whole report under fifteen lines. Numbers, not prose.
