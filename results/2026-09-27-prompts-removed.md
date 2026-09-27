# Auto mode removed 66% of permission prompts on 3,622 real commands

I replayed every Bash command Claude Code ran for me across four personal projects through jev-gate in auto mode. It approved 2,391 of 3,622 with no prompt, blocked 5, and left 1,226 to ask me. The whole run cost $0.069 in Jev, with a median of 283ms per check.

Then I gave Claude Code a small bug to fix, once without the gate and once with it. Without it, Claude hit a permission wall on 3 of its 7 tool calls and never fixed the bug. With it, 1 of 10 calls needed approval, and the bug was fixed.

Both runs on 2026-09-27 against `typesafe/jev-1.13`.

## 1. Replay of real history

[bench_prompts.py](../bench_prompts.py) reads Claude Code's session transcripts, pulls out every Bash command, masks secrets with [pool.py](../pool.py), and asks the gate about each one. The raw totals are in [prompts-2026-09-27.json](prompts-2026-09-27.json). No full command leaves the machine in the published output.

| Outcome | Commands | Share |
|---|---|---|
| Approved, no prompt | 2,391 | 66.0% |
| Still asks you | 1,226 | 33.8% |
| Blocked | 5 | 0.1% |

Where the approvals came from:

- **Jev said clearly safe:** 2,187, each with a destructive score of 0.10 or less.
- **The free shortcut:** 204 read-only commands or chains that never reached the model.

The 5 blocks: 3 commands the hard rules treat as unrecoverable, 1 remote script piped into a shell, and 1 read of a private key.

### Did it approve anything it should not have?

I pulled every approved command that matched a risky word: `rm`, `git push`, `git reset`, `curl`, `sudo`, `chmod`, `drop`, `gh release` and similar. 476 of 696 such commands were approved. I read the ones that looked worst:

- No `rm`, `git push`, `git reset` or `sudo` was approved. All of them still ask.
- Most matches were `2>/dev/null`, which only hides error output.
- The `curl` approvals were read-only requests to public APIs such as Wikisource and the GitHub API.
- The rest were `gh release list`, `gh release view`, `chmod +x` on the project's own script, and Python editing a text file.

### What still asks you

The most common first words among the 1,226: `cd` (457), `python3 -` (143), `cat` (132), `gh pr` (44), `uv run` (32), `git push` (24). Many are long chains with quotes or inline scripts, which the gate will not split and Jev was not sure about. Raising `JEV_ALLOW_BELOW` from 0.10 would approve more of them, at your own risk.

## 2. A live session

A tiny Python project with one bug, `add()` returning `a - b`. The same prompt twice: run the tests, fix the bug, rerun, show the diff. Claude Code 2.1.251 in `-p` mode with the default permission mode, where any call that needs approval is refused.

| | Without the gate | With auto mode |
|---|---|---|
| Tool calls | 7 | 10 |
| Refused for approval | 3 | 1 |
| Bug fixed | No | Yes, `a - b` became `a + b` |
| Claude cost | $0.66 | $0.83 |

Without the gate, the test run and the edit both needed approval, so Claude stopped. With the gate, every Bash call and the edit were approved at scores between 0.01 and 0.07. The one refusal was a new `conftest.py` file: Jev was unsure, at confidence 0.33, so it asked.

This run set `JEV_AUTO_TOOLS=Bash,Edit` so the fix could land. The default approves Bash only.

## Limits

- **Not every command in the replay would have prompted.** Claude Code already allows some read-only commands and anything on your own allowlist. So 66% is an upper bound on prompts removed for me, not a promise for you.
- **One person's history.** These are my projects: a note vault, a content pipeline, a CLI. Run `bench_prompts.py` on yours to get your number.
- **The live run is one task.** It shows the mechanism end to end, not an average.
- **Auto-approval is a real decision.** The gate catches mistakes, not a determined attacker. The [injection test](2026-09-20-injection-test.md) counts how many polite fake approvals got through.
