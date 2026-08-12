# Releasing

How the five packages get to PyPI. Everyday conventions are in [AGENTS.md](AGENTS.md).

Each package is released independently: its own `pyproject.toml` version, its own `docs/changelog.md`, its own `<package>/<version>` tag. The pipeline extracts the changelog section matching the tag and publishes it as the GitHub release notes. Release preparation is **mechanics only** — version bumps, changelog graduation, dependency-pin updates — never code changes.

## The branch loop

`publish_release.yml` fires on `push` to `release`, so merging is what publishes.

1. **`rel-<date>-NN` → `release`** — the PR targets `release`, never `main`. Merging it starts the publish run.
2. **The workflow tags and publishes** on the `release` ref. Never hand-tag, and never tag on `main`.
3. **`release` → `main`** with a plain merge commit (`gh pr merge <n> --merge`), so the exact released commit is preserved in `main`'s history.

The publish jobs run as `release-packages (<pkg>)` checks on the step-3 PR — watch that rollup and don't merge before it is green, since a failed publish is much easier to redo while `main` has not yet absorbed the release commit.

The `push` trigger takes no inputs, so it differs from a manual dispatch: with no `force_packages` and no `environment`, `check-package-versions` auto-detects what to build by comparing each version against PyPI and publishes to production. `priority-order: bfabric,bfabric_scripts,bfabric_app_runner` plus `max-parallel: 1` releases sequentially, so `bfabric` lands before the packages that floor on it.

## Verify offline first

Install it the way a user gets it, then import whatever the release touched:

```bash
uv venv /tmp/rel -p 3.11
uv pip install --python /tmp/rel --no-sources ./bfabric   # --no-sources: resolve deps from PyPI, not the workspace
uv pip list --python /tmp/rel | grep -i bfabric           # check the resolved dependency floor
/tmp/rel/bin/python -c "import bfabric"
```

Import the real `[project.scripts]` modules (`bfabric_scripts.cli.__main__`, `bfabric_app_runner.cli.__main__`), not a guessed path — a wrong guess raises `ImportError` and reads exactly like a broken release. Don't check entry points with `--help`: `@use_client` calls `Bfabric.connect()` before the command body runs, so `--help` can fail for config reasons unrelated to the release.

A dependent package cannot be verified before the core publishes — its freshly-bumped floor (`bfabric>=1.20.0`) excludes the current rc under PEP 440, and the push-triggered run does not pause between packages. Verify `bfabric` before opening the PR to `release`, then the dependents straight after it publishes (PyPI's index needs about a minute).

## Out-of-band dispatch (hotfixes, re-runs)

- **Never dispatch `environment: test` as a dry run.** It switches only the PyPI URL, and tag creation plus the GitHub release are ungated and run first — so a `test` run pushes the real tag and the follow-up `production` run dies at `git tag -a` before anything reaches PyPI. Verify locally and dispatch straight to `production`.
- **Pass `force_packages` explicitly.** A non-empty value makes `check_versions.py` skip the PyPI comparison entirely, so only the named packages build; confirm via `Forcing release of <pkg>` in the `check-packages` log.
- **Leave "Set as the latest release" unchecked, except for `bfabric` stable.** GitHub keeps one repo-wide badge and it belongs to the core library. `rcN` and `0.x` tags are auto-flagged as prereleases and never compete for it.

## Release candidates

- Keep **one cumulative entry** per RC line (e.g. `## [1.20.0rc2]`) describing the full changeset for the upcoming `X.Y.0`; re-date and extend that entry for the next RC rather than stacking `[…rcN]` headings below it. The published tags keep the per-RC history.
- RC entries use flat, abbreviated, headline-first bullets — the one exception to the Keep a Changelog subsections — with dev-facing changes in a trailing `Internal:` bullet.
- Graduation renames `[X.Y.0rcN]` to `[X.Y.0]` with the release date; no content merge is needed, since the entry was cumulative.
- A floor on an unreleased `bfabric` must name the rc (`bfabric>=1.20.0rc2,<1.21`) — a plain `>=1.20.0` excludes it under PEP 440, and naming it is what lets pip/uv resolve to it.

## Hotfixes (patch of an older line)

- **Find what is actually released on that line first** — check the `<pkg>/*` tags and PyPI. Your base is the latest released patch and your version is that + 1; guessing either collides with an existing tag or silently drops a shipped patch.
- **Land the fix on `main` first**, via a normal reviewed PR under `[Unreleased]`, so one commit is the source of truth.
- **Cut from the version tag, then cherry-pick**: `git checkout -b hotfix/<pkg>-X.Y.Z <pkg>/X.Y.(Z-1)`, then `git cherry-pick -x <main-commit>` after the PR merges, so the recorded SHA is permanent.
- **The version bump and the `## [X.Y.Z]` section live on the hotfix branch** — that is what the pipeline extracts into the tag and GitHub Release.
- **Publish out-of-band**: `gh workflow run publish_release.yml --ref hotfix/<pkg>-X.Y.Z -f environment=production -f force_packages=<pkg>`. Merging into `release` would mislabel a tree that is ahead on a newer line.
- **Forward-port under `[Unreleased]` only** — never backfill a `## [X.Y.Z]` section into `main`, which cannot hold a past-line patch without breaking either version or date order.
- **A fix that cannot apply to `main` leaves its changelog alone** — an `[Unreleased]` bullet would be promoted into the next release's notes, describing a change that release does not contain.
- **No PR from the hotfix branch itself** — its diff against `main` reads as a mass revert, and CI would run the old line's whole suite. The tag and GitHub Release are the record; open a PR only for the forward-port.
