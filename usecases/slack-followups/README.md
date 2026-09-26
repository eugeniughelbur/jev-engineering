# Slack follow-ups: 14 of 14 messages sorted right for $0.0002

Find the messages across every channel that are waiting on you. On 14 example messages it matched my labels on every one, first run.

## The idea

One fact runs first, as plain code: if you already replied later in the thread, the message is off the list. Everything else gets three checks from Jev:

| Check | Plain definition |
|---|---|
| `asks_me` | It asks you a question or asks you to do something. A question to the whole channel does not count |
| `decision` | Someone needs you to decide, approve, review or confirm before they can go on |
| `blocked` | The author, a customer or a team is stuck until you answer |

Any check at 0.6 or more puts it on your list.

## Try it

```bash
export OPENROUTER_API_KEY=sk-or-...
uv run followups.py messages.example.json --me alex --eval
```

Your input is a JSON list with `id`, `channel`, `author`, `text` and `you_replied_after`. Pull it from the Slack API, or have your coding agent do it.

## What the run showed

- An `@chen` message in a channel you are in scored 0.11 on `asks_me`. Jev tells a mention of someone else from a mention of you.
- "Anyone have a good article on Postgres partitioning?" scored 0.05. A question to the room is not a question to you.
- The customer escalation scored low on `decision`, 0.25, and was caught by `blocked`, 0.83. Different checks catch different kinds of "waiting on you".

## Limits

I wrote the 14 messages and their labels myself. Real Slack has threads, emoji replies and half-finished sentences. Label a day of your own messages and score against those first.
