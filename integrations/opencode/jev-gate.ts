// jev-gate for OpenCode. Copy to ~/.config/opencode/plugins/ or .opencode/plugins/.
// Set JEV_GATE_PATH to your jev_gate.py, plus JEV_GATE_MODE and OPENROUTER_API_KEY.
//
// Status: written against OpenCode's documented permission.ask hook, not yet
// run inside OpenCode. Any error leaves OpenCode's own prompt in charge.

import { spawnSync } from "node:child_process"

const GATE = process.env.JEV_GATE_PATH ?? `${process.env.HOME}/jev-engineering/jev_gate.py`

export const JevGate = async () => ({
  "permission.ask": async (input: any, output: { status: string; message?: string }) => {
    if (input?.permission !== "bash") return
    const command = input?.metadata?.command ?? (input?.patterns ?? []).join(" ")
    if (!command) return
    const run = spawnSync("python3", [GATE], {
      input: JSON.stringify({ tool_name: "Bash", tool_input: { command } }),
      encoding: "utf8",
      timeout: 8000,
    })
    try {
      const answer = JSON.parse(run.stdout || "{}")?.hookSpecificOutput
      if (answer?.permissionDecision === "allow" || answer?.permissionDecision === "deny") {
        output.status = answer.permissionDecision
        output.message = answer.permissionDecisionReason
      }
    } catch {
      // no answer: leave OpenCode's prompt in charge
    }
  },
})
