#!/bin/bash
set -euxo pipefail
chunk_dir="$(realpath $1)"
config_dir=/Users/leo/code/bfabricPy/bfabric_app_runner/examples/file_table
uv run --locked --project /Users/leo/code/bfabricPy/bfabric_app_runner/examples/file_table
  snakemake -p -s "$config_dir/Snakefile" --cores 4 -d "$chunk_dir" outputs.yml
