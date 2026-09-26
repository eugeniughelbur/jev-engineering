#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Replay a public repo's history through the router and count the routes.

    git clone --depth 400 https://github.com/fastapi/fastapi /tmp/fastapi
    uv run bench_public.py /tmp/fastapi --last 200 --out fastapi.jsonl

Each commit on the default branch stands in for one push. Two routers run
side by side:

    path     a typical path rule, the kind most teams start with
    content  the path rule plus precheck.py, which reads what the diff adds

The difference between them is what reading the content buys: commits a path
rule would wave through that the content signal sends to a full review.

Bot commits and release-note bumps are skipped, because nobody reviews them.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import precheck  # noqa: E402

# The path rule from the brief this use case started from: CI, migrations,
# anything auth-named, secrets and env files, dependency manifests, Dockerfiles.
SENSITIVE = re.compile(
    r"(^|/)\.github/workflows/|(^|/)migrations?/|\.sql$|"
    r"(auth|login|session|token|password|secret|permission|iam|policy)[^/]*$|"
    r"(^|/)\.env|\.(pem|key)$|(^|/)\.npmrc$|(^|/)\.pypirc$|"
    r"(^|/)(package\.json|requirements[^/]*\.txt|pyproject\.toml|poetry\.lock|go\.mod|Gemfile|"
    r"Cargo\.toml|setup\.py|setup\.cfg)$|(^|/)Dockerfile[^/]*$",
    re.IGNORECASE,
)
# Big pushes go to a full review whatever they touch.
MAX_CHANGED_LINES = 400
BOT = re.compile(r"\[bot\]|github-actions|dependabot|renovate", re.IGNORECASE)
SKIP_SUBJECT = re.compile(r"^(📝 )?update release notes|^bump version|^release \d", re.IGNORECASE)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          check=True).stdout


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("repo", type=Path)
    p.add_argument("--last", type=int, default=200)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    log = git(args.repo, "log", "--no-merges", "--format=%H%x09%an%x09%s", "-n", str(args.last * 3))
    commits = []
    for line in log.splitlines():
        sha, author, subject = line.split("\t", 2)
        if BOT.search(author) or SKIP_SUBJECT.search(subject):
            continue
        commits.append((sha, subject))
        if len(commits) == args.last:
            break

    with args.out.open("w") as out:
        for n, (sha, subject) in enumerate(commits, 1):
            diff = git(args.repo, "show", "--format=", "--unified=3", sha)
            paths = [f["path"] for f in precheck.files(diff)]
            changed = sum(len(f["added"]) + len(f["removed"]) for f in precheck.files(diff))
            sensitive = [x for x in paths if SENSITIVE.search(x)]
            path_route = "full" if sensitive or changed > MAX_CHANGED_LINES else "quick"

            start = time.perf_counter()
            r = precheck.decide(diff) if path_route == "quick" else None
            row = {
                "sha": sha[:10], "subject": subject[:90], "files": len(paths), "changed": changed,
                "path_route": path_route, "path_reason": sensitive[:3] or
                (["size"] if path_route == "full" else []),
                "content_route": r.route if r else "full",
                "source": r.source if r else "path",
                "categories": r.categories if r else [],
                "hits": r.hits[:6] if r else [],
                "cost_usd": r.cost_usd if r else 0.0,
                "ms": round((time.perf_counter() - start) * 1000) if r else 0,
            }
            out.write(json.dumps(row) + "\n")
            out.flush()
            print(f"[{n}/{len(commits)}] {row['path_route']:5} -> {row['content_route']:5} "
                  f"{row['source']:8} {subject[:60]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
