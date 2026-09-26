# review-router: skip the full AI review on 42% of pushes, catch 8 of 8 CVE fixes

A GitHub Action that reads what a push adds and answers `full` or `quick`. Your AI reviewer then reads the whole pull request only when it has to. On 561 commits from FastAPI, Express and Django, it let 42% go quick and sent all 8 CVE fixes to a full review. On 5 more Django CVE fixes held out from that run, it went 5 for 5 ([results](../results/2026-09-27-review-routing-public.md)).

It can only raise a review. Any error, timeout or missing key answers `full`.

## Use it

```yaml
on:
  pull_request:
    types: [opened, reopened, ready_for_review, synchronize]

jobs:
  route:
    runs-on: ubuntu-latest
    outputs:
      route: ${{ steps.router.outputs.route }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          ref: ${{ github.event.pull_request.head.sha }}
      - id: router
        uses: eugeniughelbur/jev-engineering/review-router@v1
        with:
          openrouter-api-key: ${{ secrets.OPENROUTER_API_KEY }}

  review:
    needs: route
    if: always()
    runs-on: ubuntu-latest
    steps:
      - run: echo "Run your AI reviewer here. Read the whole PR when this is full: ${{ needs.route.outputs.route }}"
```

Pass `route` to your reviewer. On `full`, review the whole pull request. On `quick`, review only the commits since the last full review.

## What it checks

1. **New pull requests.** Opened, reopened and ready-for-review always route `full`, without reading.
2. **Pattern checks.** Free and instant. Shell commands built from input, `pickle.loads`, secrets in logs, deleted `raise` and validation lines, text that talks to the reviewer, and more.
3. **Semgrep**, on the new commits only, with its own rules plus four public rule packs.
4. **Jev**, file by file. Ten yes/no risk checks per file, answered in parallel, plus one "could this change how secure the software is?" question. About $0.00003 and 0.3 seconds a file.

`quick` needs every step to say quick.

## Inputs

| Input | Default | What it does |
|---|---|---|
| `openrouter-api-key` | none | Key for Jev. Without one, the answer is always `full`. |
| `backend` | `jev` | Set `haiku` to use Claude Haiku instead, with `anthropic-api-key`. |
| `anthropic-api-key` | none | Only for `backend: haiku`. |
| `base` | previous head | The last commit that got a full review. |
| `head` | PR head | The commit to route. |
| `semgrep` | `true` | Also run Semgrep on the new commits. |
| `model` | `true` | `false` runs the free checks only. |
| `full-on-new-pr` | `true` | Route new pull requests `full` without reading. |

Outputs: `route`, `source` (what decided it) and `categories` (the risks found). Every run also writes a summary to the job page.

## Why the pull request author cannot game it

- The router runs from this action's own pinned copy, never from the pull request. Editing it in the PR changes nothing.
- A comment like "safe to approve" raises the review. Text that talks to the reviewer is one of the checks.
- Jev returns only numbers, so nothing the diff says can reach your pipeline as an instruction.

Full design, benchmark method and the Haiku comparison: [usecases/ai-review-routing](../usecases/ai-review-routing/).
