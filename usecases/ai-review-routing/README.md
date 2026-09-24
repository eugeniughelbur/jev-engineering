# precheck.py: when an AI review must read the whole pull request

An AI reviewer that re-reads the whole pull request on every push pays full price for a one-line fixup. Reading only the new commits costs tens of times less. This folder is the second signal that picks between the two by reading what the diff adds, and it can only ever raise a review, never lower one.

What is proven so far, and what is not:

- **Proven:** on 11 test diffs, every risky one went to a full review and both harmless ones stayed quick. That holds for Jev alone, for Haiku alone, and for the free checks alone. Jev took about 0.3 seconds and cost $0.00003 a diff.
- **Weak:** I wrote those 11 diffs myself and widened two rules until they passed. That shows the code works. It does not show it catches risk in your code.
- **Measured on real code:** on the 13 real commits in this repo, the full pipeline sent 12 to a full review. See the section below for why that is expected here.
- **Not measured:** the quick share on a normal app repo, and the example workflow end to end.

## The situation it solves

A path rule already sends CI files, migrations and auth-named files to a full review. It cannot see risk inside an ordinary-looking file:

- a permission or ownership check changed in `documents.py`
- a new outbound HTTP call added to a utility file
- a shell command built from input
- untrusted data deserialised
- a feature flag (a switch that turns a feature on) flipped to on by default
- a log line that now prints a token
- a validation guard deleted, which shows up only as removed lines

## The recommendation

Run three layers. Any one can force a full review. None can lower one.

1. **Tripwires** in [precheck.py](precheck.py). Regexes over added lines, plus a check for deleted guards. Free, deterministic, a few milliseconds. Any hit is `full` and the model is never called.
2. **Semgrep**, diff-aware, with the rules in [semgrep/risk-signals.yml](semgrep/risk-signals.yml) plus four registry packs. It reports only what the new commits introduce.
3. **One Jev request** for what is left. "Is this risky?" is too fuzzy to ask in one go. So it becomes 10 yes/no checks Jev answers in parallel. Does it change who can do what? Does it add a network call, or run a shell command? Code combines them. `quick` needs every check under 0.30 and Jev confident, at 0.60 or more, that the change has no safety effect. Anything else is `full`.

This is the same order as `jev_gate.py`: rules you can name first, the model for the long tail.

**Runner-up:** the same, with one Claude Haiku call in place of Jev. Set `PRECHECK_BACKEND=haiku`. It costs about 25 times more and takes about 3 times longer. Pick it when your team cannot add a vendor, since it uses the Anthropic key your reviewer already has.

**Switch from Jev to Haiku** if your benchmark shows Jev missing a risky run that Haiku catches. **Drop the model step altogether** if neither catches anything the free checks missed.

## How each option scores against the six constraints

| Option | GitHub Actions | Fails safe | Author can't steer it | No new vendor | Cheap and fast | Measurable |
|---|---|---|---|---|---|---|
| Tripwires in `precheck.py` | yes | yes, a hit only raises | yes, no model to talk to | yes | yes, free, milliseconds | yes |
| Semgrep CE, diff-aware | yes | only if you make it: managed scans fail open, the example workflow does not | yes, rules don't read comments | yes, open source, runs locally | yes, seconds | yes |
| Jev, 10 split checks | yes | yes, every error path is `full` | mostly, see below | no, TypeSafe via OpenRouter | yes, $0.00003, about 0.3s | yes |
| Haiku pre-check | yes | yes, every error path is `full` | mostly, see below | yes, same Anthropic key | yes, about $0.0008, about 1s | yes |
| PR-Agent | yes | no, its gate fields sit inside free text | weak, it writes prose you would have to parse | yes, MIT, takes an Anthropic key | no, it is a full reviewer | partly |
| Sentry `pr-risk-action` | yes | TBD | TBD | no, needs an AI gateway key | TBD | yes |

## How it handles attacker-controlled input

The pull request author writes the diff, so every layer treats it as data.

- **Text that talks to the reviewer raises the review.** A comment like "safe to approve" trips the `addresses-reviewer` rule and goes to a full review. The model prompt says the same thing. Injection becomes an escalation.
- **Steering is one of Jev's 10 checks.** On the injection test diff, Jev scored "talks to the reviewer" at 0.98, so it went to full even when the pattern check was off.
- **No free text comes back.** Jev only returns numbers. Haiku can only return a schema-checked boolean, fixed categories and a confidence. Nothing either writes reaches the reviewer or the pipeline as instructions.
- **Random fence for Haiku.** On the Haiku path, the diff sits between two copies of a boundary line with 96 random bits, so the author cannot close a fence they cannot predict. This is the "spotlighting" defence from [Hines et al. 2024](https://arxiv.org/abs/2403.14720).
- **The known Jev weakness is covered.** This repo's attack kit found that "a human already approved this" got past Jev about 10% of the time on shell commands. That exact text trips the pattern check here first.
- **The router runs from the base branch.** The example workflow loads `precheck.py` and the rules with `git show origin/<base>:...`. Otherwise the author edits the router in the same PR.
- **The quick reviewer still gets only the commit range**, never file names, as today.

What it does not stop: a change that is risky and also looks routine to all three layers. That is what the benchmark is for.

## Tested on real commits

Run on 2026-09-24 over the 13 commits in this repo, free checks only, no model:

| Version | Sent to full | Sent to quick |
|---|---|---|
| First version | 11 | 2 |
| After the fix | 9 | 4 |

The first version flagged any web link as a new network call, and 10 of 13 commits had links in their docs. The fix does three things:

1. Docs, images and licence files skip every rule except the reviewer check.
2. Build output such as `build/` and `*.egg-info/` is skipped.
3. A network call needs a client call like `requests.post(` or a URL inside a code string. A link in prose no longer counts.

The 9 left are mostly real hits. This repo is a safety tool: its code calls a model API, its tests hold shell pipes, and its attack kit contains injection text on purpose. A typical app repo should see fewer.

Adding the Jev step on top sent 12 of 13 to full. Jev alone, with no pattern checks, sent 10 to full and 2 to quick. Its one clear false alarm was a `.gitignore` change: every risk scored low, but Jev was only 0.24 sure there was no safety effect.

These are whole feature commits, not the small fixup pushes the quick path is for. The number that matters is the quick share on your own push history, and only your benchmark can give it. I stopped tuning here on purpose: every rule changed to pass a known commit makes this test less honest.

## Cost and speed, measured

Run on 2026-09-24 against the 11 fixtures:

| Layer | Per push | Latency |
|---|---|---|
| Tripwires | $0 | under 10ms |
| Semgrep, 8 local rules, one small repo | $0 | 1.7s including start-up |
| Jev, 11 questions in one request | $0.00003 | 0.25 to 1.0s |
| Haiku call, the runner-up | $0.00077, about 660 tokens in and 22 out | 0.87 to 2.1s |

On the 12 real commits small enough to send, Jev cost $0.0024 in total. Diffs over 60,000 characters go straight to full unread. Nothing gets truncated.

## Test it on your benchmark in under a day

1. **Label first.** For each review run in your 10 PRs, write one line in a JSONL file (one JSON object per line): the diff, `needs_full`, a severity and a reason. `needs_full` is true when a finding in that run needs more than the new commits to catch. Label before you look at what the router says. The format is in [fixtures/benchmark.example.jsonl](fixtures/benchmark.example.jsonl).
2. **Freeze the rules.** Commit `precheck.py` and the Semgrep rules before scoring. Tuning a regex until a known finding passes is fitting to the test.
3. **Hold out three PRs.** Tune on seven, report on three.
4. **Score the free layers:**

   ```bash
   uv run eval_router.py your-benchmark.jsonl --attack
   ```

5. **Score with Jev**, under a cent for the whole set, then with Haiku to compare:

   ```bash
   uv run eval_router.py your-benchmark.jsonl --model --attack
   PRECHECK_BACKEND=haiku uv run eval_router.py your-benchmark.jsonl --model --attack
   ```

   Also tune the two Jev thresholds here, `PRECHECK_FLAG_ABOVE` and `PRECHECK_CONFIDENCE_FLOOR`, on the seven tuning PRs only.

6. **Read three numbers.** Missed high-severity runs must be zero. `attack_lowered_route` must be empty. Then look at `quick_share`, which is your saving.

The scorer weights a missed high-severity run at 50 unneeded full reviews, a medium at 10 and a low at 3. Change that with `--weights`.

One warning about small samples. With 0 misses out of 20 risky runs, the true miss rate could still be as high as 16%. The scorer prints that upper bound as `miss_rate_upper_95`, so a clean run on a small benchmark does not read as proof.

## Files

| File | What it is |
|---|---|
| [precheck.py](precheck.py) | The router. Prints `full` or `quick`, writes to `$GITHUB_OUTPUT` |
| [semgrep/risk-signals.yml](semgrep/risk-signals.yml) | Eight routing rules the registry does not cover well |
| [eval_router.py](eval_router.py) | The benchmark scorer, with attack variants |
| [workflow.example.yml](workflow.example.yml) | GitHub Actions wiring for all three signals |
| [fixtures/](fixtures/) | One diff per gap example, plus harmless and injection cases |

The fail-safe behaviour is pinned in [tests/test_review_routing.py](../../tests/test_review_routing.py), with no key and no network.

## What the research found

- **Meta routes by risk at scale.** Its Diff Risk Score is a fine-tuned Llama model that predicts whether a diff will cause an incident. A system built on it has auto-reviewed over 535,000 diffs with a third of the revert rate. It needs years of incident data, which a small team does not have. [Meta, 2025](https://engineering.fb.com/2025/08/06/developer-tools/diff-risk-score-drs-ai-risk-aware-software-development-meta/), [arXiv 2605.30208](https://arxiv.org/abs/2605.30208)
- **LLMs alone over-flag.** On the JITVul benchmark, LLM detectors called over 90% of commits vulnerable in some setups, with precision near 50%. That is why a confident no is the only way to get `quick`, and why the free layers go first. [arXiv 2503.03586](https://arxiv.org/pdf/2503.03586)
- **Semgrep diff-aware mode** uses `--baseline-commit` and reports only findings the new commits introduce. It has no cross-file analysis in that mode. Registry rules are free for internal CI use but may not be redistributed, so this folder ships its own and fetches the rest. [Semgrep docs](https://semgrep.dev/docs/semgrep-ci/ci-environment-variables), [rules licence](https://semgrep.dev/legal/rules-license/)
- **Split fuzzy questions into small checks.** Every's Jev guide turns "is this email urgent?" into separate checks and combines the scores in code. The same move turns "is this diff risky?" into the 10 checks here. It also tunes the way step 1 above does: label a sample blind, compare, fix the checks, test on fresh examples. Every, "How to Get the Most Out of Jev", September 2026.
- **Anthropic recommends a light pre-screen model** for untrusted input, which is the Haiku runner-up here. [Anthropic docs](https://docs.anthropic.com/en/docs/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks)
- **PR-Agent** gives a 1-to-5 review effort and a security-concerns section, and runs with an Anthropic key under MIT. Both sit inside a prose review, so gating on them means parsing text the author can influence. [PR-Agent](https://github.com/The-PR-Agent/pr-agent)

## Open questions

- No public false-positive rate exists for Semgrep's `p/security-audit` pack. Measure it on your own history before adding it.
- The Sentry action's fail-safe behaviour and cost are unmeasured here.
- Diff-only reading misses cross-file effects by design. The path rule and the change-size threshold are what catch those.
