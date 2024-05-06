#!/bin/bash

clean_script() {
  target_name=$1
  target_path=$(find bfabric -name $target_name | head -n 1)
  if [ -z $target_path ]; then
    echo "No $target_name script found"
  else
    echo "Cleaning $target_path"

    set -x
    isort "$target_path"
    black "$target_path"
    ruff check "$target_path"
    set +x
  fi
}