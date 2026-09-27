#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Pick which test files a commit needs, instead of running the whole suite.

    uv run select_tests.py /path/to/repo <commit>            # the tests to run
    uv run select_tests.py /path/to/repo --bench 20          # score on history

Two steps. First, free: any test file that imports a module the commit
changed is selected, no model needed. Then Jev reads the diff once and scores
every other test file on one question, "could this change make it fail?",
forty test files to a request.

--bench replays the repo's own history. When a commit changes source code and
also edits an existing test file, that test clearly mattered. The score is
how many of those tests were selected, and how much of the suite was skipped.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from jevchecks import Check, ask  # noqa: E402

# Low on purpose: a skipped test that mattered costs far more than one extra test file.
SELECT_AT = 0.3
BATCH = 40
DIFF_CHARS = 6000


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


def test_files(repo: Path, rev: str) -> list[str]:
    return [p for p in git(repo, "ls-tree", "-r", "--name-only", rev).splitlines()
            if re.search(r"(^|/)test_[^/]*\.py$", p) and p.startswith("tests/")]


def imports(repo: Path, rev: str, path: str) -> list[str]:
    try:
        src = git(repo, "show", f"{rev}:{path}")
    except subprocess.CalledProcessError:
        return []
    return [ln.strip() for ln in src.splitlines() if re.match(r"\s*(from|import)\s+\S", ln)][:15]


def module_of(path: str) -> str:
    return path[:-3].replace("/", ".").removesuffix(".__init__")


def select(repo: Path, commit: str) -> dict:
    parent = f"{commit}^"
    changed = [p for p in git(repo, "diff", "--name-only", parent, commit).splitlines()
               if p.endswith(".py") and not re.search(r"(^|/)tests?/", p)]
    tests = test_files(repo, parent)
    diff = git(repo, "diff", "--unified=2", parent, commit, "--", *changed)[:DIFF_CHARS] if changed else ""

    modules = {module_of(p) for p in changed}
    stems = {Path(p).stem for p in changed if Path(p).stem != "__init__"}
    by_import, rest = [], []
    for t in tests:
        lines = imports(repo, parent, t)
        # Free rules first: the test imports the changed module, or it is named
        # after the changed file, the way most suites are laid out.
        imported = any(m and (f"from {m} import" in ln or f"import {m}" in ln) for ln in lines for m in modules)
        named = any(re.search(rf"(^|[/_]){re.escape(st)}([_.]|$)", Path(t).stem.removeprefix("test_") + ".") for st in stems)
        (by_import if imported or named else rest).append((t, lines))

    by_jev, cost = [], 0.0
    state = {"changed_files": changed, "diff": diff}
    for i in range(0, len(rest), BATCH):
        chunk = rest[i:i + BATCH]
        checks = [
            Check(f"t{j}", f"Test file {path}, which imports: {'; '.join(lines) or 'nothing listed'}. "
                           f"Running this test file could fail because of this change.")
            for j, (path, lines) in enumerate(chunk)
        ]
        scores, c = ask(state, checks)
        cost += c
        by_jev += [path for j, (path, _) in enumerate(chunk) if scores.get(f"t{j}", 1.0) >= SELECT_AT]

    selected = sorted({t for t, _ in by_import} | set(by_jev))
    return {"commit": commit, "changed": changed, "suite": len(tests), "selected": selected,
            "by_import": len(by_import), "by_jev": len(by_jev), "cost": round(cost, 6)}


def bench(repo: Path, limit: int, skip: int = 0) -> dict:
    rows = []
    for commit in git(repo, "log", "--no-merges", "--format=%h", "-n", "3000", *(["--skip", str(skip)] if skip else [])).split():
        status = git(repo, "show", "--name-status", "--format=", commit).splitlines()
        src = [s for s in status if re.match(r"[AM]\t[^\t]*\.py$", s) and not re.search(r"\ttests?/", s)]
        modified_tests = [s.split("\t")[1] for s in status
                          if s.startswith("M\t") and re.search(r"\ttests/(.*/)?test_[^/]*\.py$", s)]
        if not src or not modified_tests:
            continue
        r = select(repo, commit)
        r["needed"] = modified_tests
        r["caught"] = [t for t in modified_tests if t in r["selected"]]
        rows.append(r)
        print(f"{commit}: {len(r['caught'])}/{len(modified_tests)} needed tests selected, "
              f"{len(r['selected'])}/{r['suite']} files run, ${r['cost']:.4f}", file=sys.stderr)
        if len(rows) == limit:
            break
    needed = sum(len(r["needed"]) for r in rows)
    caught = sum(len(r["caught"]) for r in rows)
    run_share = sum(len(r["selected"]) / r["suite"] for r in rows) / len(rows)
    return {
        "commits": len(rows),
        "needed_tests": needed,
        "needed_tests_selected": caught,
        "recall": round(caught / needed, 3),
        "commits_with_every_needed_test": sum(len(r["caught"]) == len(r["needed"]) for r in rows),
        "avg_share_of_suite_run": round(run_share, 3),
        "cost_usd": round(sum(r["cost"] for r in rows), 4),
        "missed": [{"commit": r["commit"], "missed": sorted(set(r["needed"]) - set(r["caught"]))}
                   for r in rows if len(r["caught"]) < len(r["needed"])],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("repo", type=Path)
    p.add_argument("commit", nargs="?")
    p.add_argument("--bench", type=int, help="score on this many commits from history")
    p.add_argument("--skip", type=int, default=0, help="start the bench this many commits back")
    args = p.parse_args()
    if args.bench:
        print(json.dumps(bench(args.repo, args.bench, args.skip), indent=2))
        return 0
    if not args.commit:
        p.error("give a commit, or --bench N")
    result = select(args.repo, args.commit)
    print("\n".join(result["selected"]))
    print(f"\n{len(result['selected'])} of {result['suite']} test files, ${result['cost']:.5f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
