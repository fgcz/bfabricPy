# Contributing

This page describes some information relevant for contributing to bfabricPy.

## Development install

You should install the `dev` group as it contains some extra packages for running the tests.

```bash
pip install -e ".[dev]"
```

## Running tests

With `nox` and `uv` installed, it is as simple as running `nox` in the project root without any arguments.

## Integration tests

Note that integration tests have been moved to a separate repository. Please contact us if you are interested.

## Documentation

We currently do not have a versioning solution for the documentation, but we can add that later once it is more mature.

```bash
# To preview while you write it
mkdocs serve

# To publish after changes
mkdocs gh-deploy
```

## Release

To create a release, increase the version in `pyproject.toml`, prepare `changelog.md`,
commit everything and run `release.py`. This script will

- Create a tag and push it to GitHub
- Merge the changes to the `stable` branch and push it to GitHub
- Build the documentation and push it to GitHub Pages

The only manual step that remains is creating a release on GitHub.
To do so, you can paste the changelog section of the release and create a new release on GitHub using the tag that was created.