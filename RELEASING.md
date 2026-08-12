# Releasing

How the five packages in this workspace get to PyPI. Read this before touching a release; the
everyday conventions are in [AGENTS.md](AGENTS.md).

Each package is versioned and released independently: its own `pyproject.toml` version, its own
`docs/changelog.md`, its own `<package>/<version>` git tag. The pipeline extracts the changelog
section matching the tag and publishes it as the GitHub release notes.

Release preparation is **mechanics only** — version bumps, changelog graduation, dependency-pin
updates. It must not introduce code changes; anything that changes behavior lands on `main` first and
ships in a later cut.

## The normal flow is a branch loop, not a dispatch

`publish_release.yml` fires on `push` to `release`, so merging is what publishes.

1. **`rel-<date>-NN` → `release`.** Open the PR against `release`, never `main`. Merging it starts
   the publish run. (`release` is normally an ancestor of a `rel-*` branch cut from `origin/main`, so
   this merges cleanly.)
2. **The workflow tags and publishes** on the `release` ref. Never hand-tag, and never tag on `main`.
3. **`release` → `main`** with a plain merge commit (`gh pr merge <n> --merge`; no squash, no rebase),
   so the exact released commit is preserved in `main`'s history.

The publish jobs run as checks on the step-3 PR, so its rollup is the single place to watch:
`release-packages (<pkg>)` sits alongside the usual test/basedpyright matrix. Don't merge before it
is green — a failed publish is much easier to redo while `main` has not yet absorbed the release
commit.

**The push trigger takes no inputs, so it behaves differently from a manual dispatch.** There is no
`force_packages` and no `environment`: `check-package-versions` auto-detects what to build by
comparing each package's version against PyPI, and publishes to production. `priority-order:
bfabric,bfabric_scripts,bfabric_app_runner` plus `max-parallel: 1` releases them sequentially, so
`bfabric` lands on PyPI before the packages that floor on it.

## Verify a build offline before it goes out

Install it the way a user gets it, then import whatever the release touched:

```bash
uv venv /tmp/rel -p 3.11
uv pip install --python /tmp/rel --no-sources ./bfabric   # --no-sources: ignore workspace tool.uv.sources
uv pip list --python /tmp/rel | grep -i bfabric           # check the resolved dependency floor
/tmp/rel/bin/python -c "import bfabric"
```

Check entry points by **module import, not `--help`**: `@use_client` calls `Bfabric.connect()` before
the wrapped function runs, and the legacy argparse scripts build their parser inside the body, so
`--help` reads `~/.bfabricpy.yml` first and can fail for config reasons unrelated to the release.
Import the real modules named in each `pyproject.toml`'s `[project.scripts]`
(`bfabric_scripts.cli.__main__:main`, `bfabric_app_runner.cli.__main__:app`) — a guessed path raises
`ImportError` and reads exactly like a broken release.

**A dependent package cannot be verified before the core publishes.** Its freshly-bumped floor (e.g.
`bfabric>=1.20.0`) excludes the current rc under PEP 440, so nothing on PyPI satisfies it until
`bfabric` itself is out, and the push-triggered run does not pause between packages. Verify `bfabric`
before opening the PR to `release`, then verify the dependents straight afterwards:

```bash
uv venv /tmp/rel2 -p 3.13
uv pip install --python /tmp/rel2 --no-sources 'bfabric_scripts==<ver>' 'bfabric_app_runner==<ver>'
/tmp/rel2/bin/python -c "import bfabric_scripts.cli.__main__, bfabric_app_runner.cli.__main__"
```

After publishing, PyPI's index needs about a minute before `uv pip install <pkg>==<new>` resolves.

## Out-of-band dispatch (hotfixes, re-runs)

- **Never dispatch `environment: test` as a dry run.** That input switches only the PyPI URL. *Create
  and push tag* and *Create GitHub Release* are ungated and run **before** the publish step, so a
  `test` run pushes the real `<pkg>/<version>` tag and opens the draft release — and the follow-up
  `production` run then dies at `git tag -a` ("already exists") before anything reaches PyPI. Verify
  locally instead and dispatch straight to `production`.
- **Pass `force_packages` explicitly.** A non-empty value makes `check_versions.py` skip the PyPI
  version comparison entirely, so only the named packages build. Confirm via `Forcing release of
  <pkg>` in the `check-packages` log.
- **Leave "Set as the latest release" unchecked when publishing the draft, except for `bfabric`
  stable.** GitHub keeps one repo-wide "Latest release", so a stable non-core release — or a patch of
  an older line — would take the badge from the core library. `rcN` and `0.x` tags are auto-flagged
  as prereleases and never compete for it.

## Release candidates

- **One cumulative pre-release entry, not a stack.** While a version is in RC, keep a *single*
  changelog entry for it (e.g. `## [1.20.0rc2]`) describing the **full** changeset for the upcoming
  `X.Y.0`. When cutting the next RC, re-date and extend that same entry and bump the `rcN` suffix —
  do not add a separate `[…rcN]` heading below the previous one. Per-RC history is preserved by the
  published tags and GitHub releases.
- **RC entries use flat, abbreviated bullets, headline-first** — the one exception to the Keep a
  Changelog subsections normal entries use. User-facing headlines come first; dev-facing
  typing/tooling changes go in a trailing `Internal:` bullet.
- **Graduation** renames the `[X.Y.0rcN]` heading to `[X.Y.0]` with the release date. No content merge
  is needed, since the entry was cumulative.
- **Cross-package dependency floors must name the rc** when a package uses a feature from an
  unreleased `bfabric` (e.g. `bfabric>=1.20.0rc2,<1.21`). A plain `>=1.20.0` *excludes* `1.20.0rc2`
  under PEP 440, and naming the prerelease is also what lets pip/uv resolve to it.

## Hotfixes (patch release of an older line)

- **First, find what's actually released on that line.** Check the `<pkg>/*` git tags and PyPI for the
  latest released patch: that tag is your base and your new version is that patch + 1. Skipping this
  is the classic hotfix error — you either collide with an existing tag or silently drop an
  already-shipped patch (base `1.19.0` → ship `1.19.3`, dropping `1.19.1`/`1.19.2`).
- **Land the fix on `main` first, via a normal reviewed PR** (under `[Unreleased]`), so a single
  commit is the source of truth. Don't build the hotfix branch first and reverse-port afterwards.
- **Cut the hotfix branch from the version tag, then cherry-pick the merged fix.** `release`/`main`
  have moved ahead when the newest line is unreleased or in RC:
  `git checkout -b hotfix/<pkg>-X.Y.Z <pkg>/X.Y.(Z-1)`, then `git cherry-pick -x <main-commit>`
  **after** the PR merges, so the recorded SHA is permanent.
- **The version bump and the `## [X.Y.Z]` changelog section live on the hotfix branch** — that is what
  the pipeline extracts into the tag and GitHub Release.
- **Publish out-of-band, don't merge into `release`** (which is ahead on a newer line and would be
  mislabelled):
  `gh workflow run publish_release.yml --ref hotfix/<pkg>-X.Y.Z -f environment=production -f force_packages=<pkg>`.
  The branch then lives on as the release record; it has no merge target.
- **Forward-port to `main` as a normal PR, `[Unreleased]` only.** Cherry-pick with `-x` so `1.X.0`
  doesn't regress, and note it inline (e.g. "also released as the X.Y.Z hotfix"). Do **not** backfill
  a `## [X.Y.Z]` section into `main`: a past-line patch can't sit in a version-descending changelog
  without breaking either version or date order, and the tag + GitHub Release already record it.
- **A fix that can't apply to `main` leaves `main`'s changelog alone.** Some hotfixes only constrain
  the old line — a dependency cap, say, when `main` has already migrated past the broken API. With
  nothing to forward-port there is nothing to document, and an `[Unreleased]` bullet would be promoted
  into the next release's notes, describing a change that release doesn't contain.
- **No PR from the hotfix branch itself.** Its diff against `main` reads as a mass revert, and PR CI
  would run the old line's whole nox suite. Push the branch and let the tag and GitHub Release be the
  record. Open a PR only for the forward-port.
