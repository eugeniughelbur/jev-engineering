# Inbox triage: 16 of 16 emails sorted right for $0.0003

Find the emails that need you now, out of everything else. On 16 example emails it matched my labels on every one, on the first run, with thresholds set before it ran. The whole batch cost $0.0003 in Jev.

## The idea

"Is this urgent?" means something different to everyone, so a model asked that directly is guessing at your definition. Split it instead:

| Check | Plain definition |
|---|---|
| `human` | A real person wrote this to you personally |
| `waiting` | Someone asked you for something or is blocked by you |
| `cost` | Ignoring it for a day costs money, access, security, a deal or trust |
| `soon` | It names a deadline in the next two days |

Jev scores all four at once. Then ordinary code decides, in a rule you can read in [triage.py](triage.py):

1. Mass mail, with a `List-Unsubscribe` header, is never urgent. No model needed.
2. A real cost, `cost` of 0.7 or more, is urgent even from a machine. A security alert or a pager is not written by a person and still needs you.
3. Otherwise it needs a person who is waiting on you: `human` of 0.5 or more and `waiting` of 0.6 or more.

## Try it

```bash
export OPENROUTER_API_KEY=sk-or-...
uv run triage.py emails.example.json --eval
```

Swap in your own export: a JSON list with `id`, `from`, `subject`, `body` and `list_unsubscribe`. Add `urgent` to score it.

## What the run showed

- The security alert and the pager alert were caught by `cost`, with `human` near zero. A "must be a person" rule would have missed both.
- Cold sales and the recruiter scored high on `waiting`, 0.80 and 0.83. They stayed off the list only because `human` came in under 0.5, at 0.37 and 0.47. Those are the close calls to watch in your own mail.

## Limits

I wrote the 16 emails and their labels myself, before running Jev. They are cleaner than a real inbox. Tune on a sample of your own mail you have already judged, then test on fresh mail before trusting it on everything.
