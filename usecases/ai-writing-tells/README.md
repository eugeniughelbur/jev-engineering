# AI writing tells: 12 of 12 examples, 2 false alarms in 40 real paragraphs

Flag the paragraphs that read like AI wrote them, and name the tell, so an agent can rewrite only those. It caught all 6 AI-style examples and passed all 6 human ones. On 40 paragraphs from Django's human-written docs, it flagged 2.

## The idea

"Does this sound like AI?" is too vague to score. Split it into tells:

- **Free, by regex:** a list of overused words and stock phrases, the `SLOP` pattern in [tells.py](tells.py). Edit it to match your own taste.
- **Jev, one question each:** "not X but Y" constructions, three-fragment rhythm like "Faster. Smarter. Better.", claims with no concrete detail, chatbot voice, and hedging.

A paragraph is flagged when any regex hits or any Jev tell scores 0.7 or more. The output names each tell, which is what makes it useful in a loop: draft, check, rewrite what it flags, check again.

## Try it

```bash
export OPENROUTER_API_KEY=sk-or-...
uv run tells.py paragraphs.example.json --eval
uv run tells.py my-draft.md
```

A markdown file is split into paragraphs. Headings, code, lists and tables are skipped.

## What the run showed

| Test | Result | Jev cost |
|---|---|---|
| 6 AI-style and 6 human paragraphs I wrote | 12 of 12 right | $0.00023 |
| 40 paragraphs from Django's security and overview docs, all human | 2 flagged | $0.00084 |

The two Django false alarms: one for `hedge`, and one for a stock phrase from the regex list that Django uses in its plain sense, about a newsroom. Every AI example also scored high on `generic`, so a vague paragraph is the strongest single signal.

## Limits

My 12 examples are clear-cut. Real AI text edited by a person will be harder. Check your own drafts against paragraphs you have already judged before you trust the threshold.
