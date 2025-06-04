## Monorepo Setup

The project is built in a single repository, which hosts 3 Python packages:

- `bfabric`
- `bfabric-scripts`
- `bfabric-app-runner`

Each of these projects has its independent `pyproject.toml` and package.
`bfabric-scripts` and `bfabric-app-runner` each depends on the `bfabric` package.

### Direct references

[Direct references](https://peps.python.org/pep-0440/#direct-references) allow to reference a Git repository directly.
This is not supposed to be used for deployed versions, but it can be useful during development, for instance if you add a new feature
to `bfabric` and need it in `babric-scripts`, but you do not want to deploy that yet.

Because of the subdirectory structure the arguments when specifying the dependency are:

- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric`
- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_scripts`
- `git+https://github.com/fgcz/bfabricPy@main#subdirectory=bfabric_app_runner`

You can omit `@main` but it's included in the example to show how to specify a specific branch or tag.

If you use `hatchling` as your `pyproject.toml` builder, then you need to ensure direct references are allowed:

```toml
[tool.hatch.metadata]
allow-direct-references = true
```
