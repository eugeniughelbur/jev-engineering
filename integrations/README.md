# jev-gate in other coding agents: Codex, Cursor, OpenCode

The same gate and the same rules run in every agent. Only the wiring changes. Set `JEV_GATE_MODE=auto` and `OPENROUTER_API_KEY` in the environment the agent starts from, and replace `/absolute/path/to/jev-engineering` with where you cloned this repo.

| Agent | How it plugs in | Tested |
|---|---|---|
| Claude Code | The plugin, `claude plugin install jev-engineering@jev-engineering` | Yes, in live sessions |
| Codex | A `PreToolUse` hook, same format as Claude Code | Hook output tested offline. A live Codex run is still to do |
| Cursor | A `beforeShellExecution` hook with `--agent cursor` | Output tested offline, not yet inside Cursor |
| OpenCode | A plugin on the `permission.ask` hook | Written from the docs, not yet run |

Every adapter fails open. If the gate errors, times out or has no key, the agent shows its own prompt as normal.

## Codex

Copy [codex/hooks.json](codex/hooks.json) to `~/.codex/hooks.json`, or merge it into an existing one. Hooks in a project's own `.codex/` folder only load once you trust that project, so the user-level file is the reliable place.

## Cursor

Copy [cursor/hooks.json](cursor/hooks.json) to `~/.cursor/hooks.json` for every project, or `.cursor/hooks.json` for one. The gate answers Cursor's `{"permission": ...}` format when it is sure, and prints nothing otherwise, which leaves Cursor's own prompt in charge.

## OpenCode

Copy [opencode/jev-gate.ts](opencode/jev-gate.ts) to `~/.config/opencode/plugins/`, and set `JEV_GATE_PATH` to your `jev_gate.py`.
