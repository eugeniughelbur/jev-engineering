# Recipes, one per tool

Every recipe is the same idea wearing different clothes: intercept the action, ask Jev, act on the number. What changes is where you intercept, and whether you fail open or closed.

## Fail open or fail closed

Decide this before you write any code.

**Fail open** means an error, timeout or missing key falls back to the harness's own permission prompt. Use it for a coding agent on your own machine, where a network blip that bricks your session is worse than a missed check.

**Fail closed** means the same conditions escalate to a human instead of permitting. Use it for anything with side effects outside your laptop: money, email, production.

`jev_gate.py` here fails open, because it was built for a coding agent. Published Hermes gates fail closed, because they were built for an agent that sends things. Neither is more correct.

## Plain HTTP

The base every other recipe wraps.

```bash
curl -X POST https://openrouter.ai/api/v1/systemone \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "typesafe/jev-1.13",
    "state": "rm -rf ./build",
    "questions": {
      "destructive": {
        "type": "noul",
        "instructions": "This command destroys data that is hard to recover."
      }
    }
  }'
```

TypeSafe's own endpoint, Cloudflare Workers AI, Vercel and Netlify expose the same request shape. Pick whichever you already pay for.

## Claude Code

The cleanest gate point of any tool here, because the hook runs whether the model likes it or not.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{ "type": "command", "command": "/absolute/path/to/jev_gate.py" }]
      }
    ]
  }
}
```

Exit 0 permits, exit 2 blocks. Two details decide whether this works:

1. Send the recent user message and the proposed command. Do not send the model's own reasoning or prior tool output, or the agent can write its own permission slip.
2. Fail open on every error path.

Start in `observe` mode. If you already run with permissions skipped, enable hard rules only at first, so you add zero new prompts. Adding friction is how these tools get uninstalled.

## Codex

Two jobs, two places.

**Approvals.** Same hook shape as Claude Code. Published gates write handlers for the prompt event and the pre-tool event together, using the user's own prompt as the record of what was authorized.

**Model routing.** Run a local server, declare it as a curated model, and classify each turn into a cheap or an expensive model. One published backtest over 237 real turns reported roughly 60% lower cost. One tuning note from the same report: when confidence drops below 0.5, send the turn to the middle model, not the top one. Falling back to the frontier model eats about 80% of the savings.

**MCP.** One command.

```bash
codex mcp add jev --env TYPESAFE_API_KEY=ts_... -- node /path/to/jev-mcp/dist/index.js
```

## Cursor, and any MCP client

Write the server once and every MCP client can use it.

```json
{
  "mcpServers": {
    "jev": {
      "command": "node",
      "args": ["/absolute/path/to/jev-mcp/dist/index.js"],
      "env": { "TYPESAFE_API_KEY": "ts_..." }
    }
  }
}
```

One caution that matters more than it looks. An MCP tool is something the model chooses to call. A hook is something that runs regardless. For a safety gate you want the hook. Use MCP when you want the agent to be able to ask for a judgement, not when you need to force one on it.

## LangChain

Two pieces of middleware ship for this: one routes between models, one screens tool calls.

```python
from langchain.agents import create_agent
from langchain_typesafe.experimental.middleware import AutoModeMiddleware

guardrail = AutoModeMiddleware(tools=["bash"])
agent = create_agent("openai:gpt-5.6-luna", middleware=[guardrail])
```

## Pydantic AI

The one that inverts your habits. The question does not go in the prompt. The question goes on the output type.

```python
from enum import Enum
from pydantic import BaseModel, Field
from pydantic_ai import Agent

class Verdict(str, Enum):
    run = 'run'
    reject = 'reject'
    ask = 'ask'

class Handling(BaseModel):
    verdict: Verdict
    irreversible: bool = Field(
        description='Would running this destroy data or leak secrets?'
    )

agent = Agent('typesafe:jev-latest', output_type=Handling)
result = agent.run_sync('rm -rf ./build')
```

A boolean field becomes a yes/no question. An enum becomes a choice. A field description becomes the instruction. Raise `typesafe_boolean_threshold` where a false positive is expensive, and pair it with a fallback chat model for anything Jev cannot handle.

One gotcha from the docs: reordering the options in a `Literal` can shift the answer. Keep the order stable and version it with your thresholds.

## Hermes

Published gates here fail closed and sit between the built-in hardline blocks and the normal approval flow. They also redact sensitive arguments before sending and keep a metadata-only audit log. Both choices are right for an agent with side effects.

## Pi

Community extensions exist for tool gating, policy enforcement and context pruning. The context-pruning ones are the interesting branch: the same model that decides whether an action is safe can decide whether a piece of context is worth keeping.

## n8n

Community nodes let a workflow branch on a typed question. This is the no-code route, and it is the one to hand someone who will never open a terminal.

## Grok Build

No native support. The request is filed and open. Until it ships, use the HTTP recipe or an MCP server.

## What to log, whatever you pick

Log the question text, the returned numbers, the threshold in force, and the verdict. You will never get an explanation out of the model, so the log is the entire audit trail that will ever exist. Version the questions, the criteria and the thresholds together as one unit, because changing any of them changes the meaning of every number you logged before.
