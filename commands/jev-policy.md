---
description: Show the rules in force, where each came from, and pull the team's latest
---

The rules are a file, not code. Three layers merge: the shipped default, the team policy, and the user's own overrides.

1. Show what is in force:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/policy.py" show
```

Read the trace at the top out loud to the user. It names which layer contributed each rule and each threshold, and it names anything their override tried to loosen and got refused.

2. Explain the one rule that matters if they ask why something was ignored. Layers add rules and tighten thresholds. They never loosen. A shared rule any member can quietly switch off is not a shared rule.

3. If `JEV_POLICY_URL` is set, offer to pull the team's latest:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/policy.py" pull
```

It validates every regex before caching, and keeps the previous copy if the fetch fails. If the cached copy is more than 30 days old, `show` says so, and you should suggest pulling.

4. To add a personal rule, write `~/.jev-gate/policy.local.json`. Only the keys they want to change:

```json
{
  "thresholds": { "deny_above": 0.75 },
  "hard_deny": [
    { "pattern": "\\bgh\\s+repo\\s+delete\\b", "reason": "deletes a repository" }
  ]
}
```

Always run `policy.py check` after editing. A broken regex means that rule never fires, silently.

5. If they want a rule to apply to everyone, it belongs in the team policy, not in their local file. Say so plainly instead of helping them keep it private.
