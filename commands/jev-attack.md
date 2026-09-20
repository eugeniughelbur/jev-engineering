---
description: Attack your own gate with 300 prompt injections and report what got through
---

Find out whether the gate holds before trusting it. This spends real money, about half a cent, so confirm first.

1. Tell the user what it will do and what it costs: roughly 300 calls against `typesafe/jev-1.13`, about $0.006, taking two to three minutes. Ask them to confirm.

2. Offer the quick version if they want a smaller bill:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/attack_test.py" --quick
```

Full run:

```bash
uv run "${CLAUDE_PLUGIN_ROOT}/attack_test.py"
```

3. Before running, point out that `fixtures/commands.json` ships with generic commands. Their own shell history is the only fixture that matters. Offer to build a fixture set from their history, dangerous and safe split, if they want a result that means something.

4. Read the output and lead with the answer: how many dangerous commands got through, and how many safe commands were wrongly blocked. Both numbers matter. A gate that blocks safe work gets uninstalled.

5. Explain the two attack shapes in plain words:
   - the blunt one tells the model to ignore its instructions. In testing it failed to get in, and caused false denials instead.
   - the authority one claims a human already approved the action. That is the one that works.

6. Point at the confidence floor table. Say which floor they should set, and say the price of it: the share of normal traffic that would start asking.

7. Name any command that flipped under every framing. Those belong in `HARD_DENY` in `jev_gate.py`, not in a probability. Offer to add them.

Compare against the reference run in `results/2026-09-20-injection-test.md` if it helps, but their numbers are the ones that count.
