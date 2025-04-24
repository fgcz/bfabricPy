#!/bin/bash
set -euxo pipefail
chunk_dir="$(realpath $1)"
config_dir=/scratch/leo/code/bfabricPy/bfabric_app_runner/examples/file_table
uv run --locked --project "$config_dir" \
  snakemake -p -s "$config_dir/Snakefile" --cores 4 -d "$chunk_dir" outputs.yml
