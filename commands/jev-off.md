---
description: Turn auto mode off, back to logging only
---

Switch jev-gate back to observe mode, which logs every decision and changes nothing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/jev_gate.py" --mode observe
```

Tell the user it applies from the next command, and that `/jev-on` turns auto mode back on.
