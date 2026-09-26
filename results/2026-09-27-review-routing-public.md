# Review routing on FastAPI, Express and Django: 8 of 8 CVE fixes caught

A path rule sent 8 CVE fixes in these three repos to a quick review, because the files had ordinary names. Reading the diff with Jev sent all 8 to a full review. It still let 42% of 561 commits go quick, for $0.029 in Jev across the whole run.

Run on 2026-09-27 with [bench_public.py](../usecases/ai-review-routing/bench_public.py). Raw rows are in [review-routing/](review-routing/).

## Setup

| Repo | Commits replayed | Head at run time |
|---|---|---|
| fastapi/fastapi | 161 | `192b121`, 2026-09-25 |
| expressjs/express | 200 | `9a34acf`, 2026-09-15 |
| django/django | 200 | `4fab678`, 2026-09-26 |

Each commit on the default branch stands in for one push. Bot commits and release-note bumps are skipped. Two routers run side by side:

- **Path rule.** Full review for CI workflows, migrations, SQL, auth-named files, env and key files, dependency manifests, Dockerfiles, and any commit over 400 changed lines. Quick otherwise.
- **Path rule plus content.** The same, then `precheck.py` reads what each quick commit adds: pattern checks first, then Jev file by file. Semgrep was off for this run.

## Results

| Repo | Quick, path rule alone | Quick, with content check | Sent to full by the content check |
|---|---|---|---|
| FastAPI | 100 of 161, 62% | 70, 43% | 30 |
| Express | 105 of 200, 52% | 69, 34% | 36 |
| Django | 161 of 200, 80% | 95, 48% | 66 |
| **All** | **366 of 561, 65%** | **234, 42%** | **132** |

The Jev step took a median of 320ms per commit. No request failed.

## The CVE fixes a path rule would miss

Every commit here fixes a published vulnerability, and every one touched only ordinary-looking files:

| Repo | Commit | What decided full |
|---|---|---|
| Express | `sec: security patch for CVE-2024-51999` | Jev |
| Express | `Revert "sec: security patch for CVE-2024-51999"` | pattern check, a deleted guard |
| Django | `Fixed CVE-2026-15920 -- Made display_for_field() validate URLs before rendering` | Jev |
| Django | `Fixed CVE-2026-15337 -- Mitigated potential DoS in check_for_language()` | pattern check, a deleted guard |
| Django | `Fixed CVE-2026-15307 -- Blocked raster strings and dicts in spatial lookups` | pattern check, a deleted guard |
| Django | `Fixed CVE-2026-53878 -- Prevented newlines from being accepted in DomainNameValidator` | Jev |
| Django | `Fixed CVE-2026-53877 -- Prevented heap buffer over-read when creating GDALRaster` | Jev |
| Django | `Fixed CVE-2026-48588 -- Prevented caching of responses that set cookies` | pattern check, a deleted guard |

Pattern checks ran first and caught 4, each through a changed line holding a `raise` or validation call. Jev caught the other 4, mostly through its catch-all question: "could this change how secure the software is?"

I then ran Jev alone on the 4 the pattern checks took. It sent all 4 to full as well. **So Jev by itself caught 8 of 8, and the pattern checks by themselves caught 4 of 8.**

Other security-relevant commits it raised include Django's `Made admin views raise PermissionDenied consistently` and `Omitted inlines without add permission on save-as-new`.

## What stayed quick

The security-worded commits that stayed quick were docs and test changes: security policy links, the CVE archive page, and a test that references a CVE without touching the fix. None changed runtime code.

## What this does not show

- **A fix routed to full is not a bug found.** This measures which commits get the deeper review, not what the reviewer then catches.
- **Commits are not pushes.** FastAPI and Express squash pull requests, so each commit is a whole PR. Real fixup pushes are smaller, so the quick share on push history should be higher.
- **Some raised commits are noise.** Of the 132 raised, 57 named a specific risk. The other 75 were raised because Jev was not confident the change had no safety effect. That is the price of routing on doubt.
- **Security wording was matched by hand.** I searched subjects for CVE, security, XSS, permission and similar words. A vulnerability fix with a plain subject would not appear in the table above.
