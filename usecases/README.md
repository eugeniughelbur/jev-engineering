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
| [ai-review-routing](ai-review-routing/) | Must the AI code reviewer read the whole pull request, or only the new commits? | Working. Jev by default, Haiku as runner-up. 11 test diffs and 13 real commits |

## Adding one

Start from a real brief: the situation, the constraints, what you already tried. Research it, then write the folder so that someone with the same problem can copy it and run the test on day one. If a number in the README was not measured, mark it TBD.
