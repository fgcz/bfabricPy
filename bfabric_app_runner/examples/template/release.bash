#!/bin/bash
set -euxo pipefail
pkg_version=$(uv version --short)
uv lock
uv build -o dist/${pkg_version}
uv export --format pylock.toml --no-emit-project > dist/${pkg_version}/pylock.toml
