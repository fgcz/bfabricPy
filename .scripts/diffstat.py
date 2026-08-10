#!/usr/bin/env python3
"""
Summarize a branch's diff as added/removed/net lines, grouped by directory.

Answers "how big is this change, really" by bucketing ``git diff --numstat`` against the merge
base, so a branch dominated by tests or docs can still be judged on the production code it
touches. Renames count as the edit they contain rather than as a delete plus an add; pass
``--no-renames`` for the opposite reading.

Usually invoked as ``nox -s diffstat -- <args>``; runnable directly since it needs no dependencies.

Usage:
    .scripts/diffstat.py                                # vs merge base with main, 2 levels deep
    .scripts/diffstat.py --base release --depth 1
    .scripts/diffstat.py -x tests -x '*/docs/*'         # drop paths from the table and totals
    .scripts/diffstat.py --no-renames
"""

import argparse
import re
import subprocess
import sys


def git(*argv: str) -> str:
    """Run a git command and return its stdout."""
    result = subprocess.run(["git", *argv], text=True, capture_output=True, check=False)
    if result.returncode != 0:
        print(f"git {' '.join(argv)} failed: {result.stderr.strip()}", file=sys.stderr)
        raise SystemExit(1)
    return result.stdout


def numstat_path(raw: str) -> str:
    """Resolve the post-rename path of a ``git diff --numstat`` entry.

    Renames arrive either with the common prefix/suffix factored out (``a/{old => new}/f.py``,
    or ``a/{ => new}/f.py`` when one side is empty) or spelled out in full (``old.py => new.py``).
    Left as-is, each would land in a bucket of its own instead of under its directory.
    """
    match = re.match(r"(.*)\{(.*) => (.*)\}(.*)", raw)
    if match:
        return (match.group(1) + match.group(3) + match.group(4)).replace("//", "/")
    return raw.split(" => ", 1)[-1]


def group_key(path: str, depth: int) -> str:
    """Truncate a path to its first ``depth`` components, keeping shallower paths whole."""
    parts = path.split("/")
    return "/".join(parts[:depth]) if len(parts) > depth else path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--base", default="main", help="ref to diff against; its merge base with HEAD is used")
    parser.add_argument("--depth", type=int, default=2, help="number of path components to group by")
    parser.add_argument("-x", "--exclude", action="append", default=[], help="pathspec to exclude, repeatable")
    parser.add_argument("--no-renames", action="store_true", help="count a rename as a delete plus an add")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    base = git("merge-base", args.base, "HEAD").strip()
    diff = ["diff", "--numstat"] + (["--no-renames"] if args.no_renames else [])
    diff += [base, "HEAD", "--", *(f":!{pattern}" for pattern in args.exclude)]

    buckets: dict[str, list[int]] = {}
    files = binary = 0
    for line in git(*diff).splitlines():
        added, removed, raw = line.split("\t", 2)
        files += 1
        if added == "-":
            # numstat reports no line counts for binary files
            binary += 1
            continue
        entry = buckets.setdefault(group_key(numstat_path(raw), args.depth), [0, 0])
        entry[0] += int(added)
        entry[1] += int(removed)

    if not files:
        print(f"No changes between {args.base} ({base[:8]}) and HEAD")
        return 0

    rows = sorted(((a - r, a, r, key) for key, (a, r) in buckets.items()), reverse=True)
    rows.append((sum(r[0] for r in rows), sum(r[1] for r in rows), sum(r[2] for r in rows), "TOTAL"))
    width = max(len(row[3]) for row in rows)
    rule = f"{'-' * 8}  {'-' * 8}  {'-' * 8}  {'-' * width}"

    excluded = f", excluding {' '.join(args.exclude)}" if args.exclude else ""
    print(f"\n{files} files changed vs {args.base} (merge base {base[:8]}){excluded}")
    if binary:
        print(f"{binary} binary file(s) counted in that total but contributing no lines")
    print(f"\n{'net':>8}  {'added':>8}  {'removed':>8}  {'path':<{width}}")
    print(rule)
    for net, added, removed, key in rows:
        if key == "TOTAL":
            print(rule)
        print(f"{net:>+8}  {added:>+8}  {f'-{removed}':>8}  {key:<{width}}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
