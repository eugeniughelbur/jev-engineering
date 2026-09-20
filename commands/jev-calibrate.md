---
description: Read a week of your own gate decisions and turn them into your thresholds and rules
---

Turn the user's own decision log into their settings. The defaults shipped with this plugin came from someone else's machine.

1. Run the calibrator:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/calibrate.py"
```

If `uv` is missing, fall back to `python3`.

2. If it reports fewer than 7 days of log, stop. Tell the user to keep running in observe mode and come back. Do not recommend thresholds from a thin log.

3. Read the output and give the user a verdict first, in one sentence: is the gate ready to enforce, or does the fast path need widening first? The tool flags this when more than a quarter of their work would have been interrupted.

4. Walk them through what it found, in this order:
   - the interruption cost, because that is the number they will feel
   - the threshold sweep
   - the fast-path regexes it suggests, which they paste into `FAST_ALLOW` in `jev_gate.py`
   - the hard-rule candidates, which they add to `HARD_DENY` only if those commands should always be stopped

5. Offer the labelling pass. Without labels the sweep shows interruption cost only. With labels it shows how many dangerous commands each threshold would miss. Run it only if they say yes, because it is interactive:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/calibrate.py" --label
```

6. Ask before writing anything. `--apply` overwrites threshold lines in `.env`. Never run it unprompted.

7. End with the next step: switch `JEV_GATE_MODE` to `guard`, and re-run this monthly because their commands drift and the model gets retrained.
