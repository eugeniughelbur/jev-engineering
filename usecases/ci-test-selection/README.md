# CI test selection: tried, not ready, 58% recall

Status: **do not use this to skip tests.** It picked 58% of the tests that mattered on commits it had never seen. A selector that misses 4 in 10 needed tests is worse than running the whole suite.

The code and the benchmark stay here because the negative result is useful. If you get it past 95%, open a pull request.

## What it does

[select_tests.py](select_tests.py) picks which test files a commit needs, in two steps:

1. **Free rules.** A test file is picked when it imports the changed module, or when it is named after the changed file, like `frontend.py` and `test_frontend.py`.
2. **Jev.** Every other test file gets one question, "could this change make it fail?", with the diff and the test's import lines. Forty test files go in one request. A score of 0.3 or more picks it.

## How it was scored

On FastAPI's own history. When a commit changes source code and also edits a test file that already existed, that test clearly mattered. The score is how many of those tests were picked.

| Run | Commits | Needed tests picked | Every needed test picked | Share of suite run | Jev cost |
|---|---|---|---|---|---|
| First version, recent commits | 14 | 7 of 18, 39% | 6 of 14 | 1% | $0.03 |
| Rules fixed, same commits | 14 | 12 of 18, 67% | 11 of 14 | 4.5% | $0.03 |
| Holdout, older commits never tuned on | 20 | 271 of 541, 50% | 7 of 20 | 8.1% | $0.045 |
| Holdout without sweeping commits | 13 | 11 of 19, 58% | 6 of 13 | 5.2% | from cache |

A "sweeping" commit edits more than 5 test files at once. In this history those were style changes, not 70 affected tests.

## Why it misses

- **Tests import the package, not the file.** FastAPI tests say `from fastapi import FastAPI`, so a change to `fastapi/routing.py` matches no import line.
- **The diff says little about who calls the code.** Jev sees what changed and a test's imports. It cannot see that `test_custom_response` goes through the changed code three calls deep.
- **Tutorial tests hide their target.** Many tests run example apps in `docs_src/`, so neither the name nor the imports point at the library file.

## What would work better

Real coverage data. Tools like `pytest-testmon` record which lines each test runs, then pick tests by the lines a commit touches. Jev could still help on top of that, for the files coverage says nothing about.
