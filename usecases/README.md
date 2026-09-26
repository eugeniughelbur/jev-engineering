# Use cases: 1 folder per situation

Each folder solves one real decision an AI system has to make, with working code, a test set and measured numbers. The gate in the repo root answers "is this action safe". These answer the questions around it.

Every folder follows the same shape:

1. **The situation.** Who runs what, and what goes wrong today.
2. **The recommendation**, a runner-up, and what would make you switch.
3. **A table** scoring each option against the constraints that matter.
4. **Code you can drop in**, and fixtures that show it working.
5. **A way to test it** on your own data in under a day.

| Use case | The decision | Status |
|---|---|---|
| [ai-review-routing](ai-review-routing/) | Must the AI code reviewer read the whole pull request, or only the new commits? | 561 public commits: 42% skip the full review, 8 of 8 CVE fixes caught. Ships as a [GitHub Action](../review-router/) |
| [inbox-triage](inbox-triage/) | Which emails need me now? | 16 of 16 examples, $0.0003 |
| [ai-writing-tells](ai-writing-tells/) | Which paragraphs read like AI wrote them, and why? | 12 of 12 examples, 2 false alarms in 40 real paragraphs |
| [slack-followups](slack-followups/) | Which messages across every channel are waiting on me? | 14 of 14 examples, $0.0002 |

All four use the same move: split one fuzzy question into a few yes/no checks with plain definitions, let Jev score them in parallel, and combine the scores in code you can read. The shared helper is [jevchecks.py](jevchecks.py), standard library only.

## Adding one

Start from a real brief: the situation, the constraints, what you already tried. Research it, then write the folder so that someone with the same problem can copy it and run the test on day one. If a number in the README was not measured, mark it TBD.
