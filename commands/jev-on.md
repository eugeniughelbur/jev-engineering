---
description: Turn on auto mode, so clearly safe commands run with no permission prompt
---

Turn jev-gate's auto mode on for the user.

1. Show what auto mode would have done so far, from the log:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/jev_gate.py" --stats
```

2. Check the key. Confirm `OPENROUTER_API_KEY` or `TYPESAFE_API_KEY` is set, without printing any part of it. If neither is set, stop and tell the user: without a key only the free rules can answer, so almost nothing gets auto-approved. Point them at adding `"env": {"OPENROUTER_API_KEY": "sk-or-..."}` to `~/.claude/settings.json`, typed by them, never pasted into this chat.

3. Switch the mode:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/jev_gate.py" --mode auto
```

4. Tell the user, in three lines:
   - clearly safe commands now run with no prompt
   - clearly dangerous ones are blocked, with the reason
   - anything unsure still asks them, and `/jev-off` switches it back
