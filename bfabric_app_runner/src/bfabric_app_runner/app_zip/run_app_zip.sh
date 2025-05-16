#!/usr/bin/env bash

# Helper function to check if file is newer than directory
is_newer() {
  local ZIP="$1"
  local DIR="$2"

  # If directory doesn't exist, zip is "newer"
  if [ ! -d "$DIR" ]; then
    return 0  # True (0 in bash)
  fi

  # Compare modification times (works on Linux and macOS)
  if [[ "$OSTYPE" == "darwin"* ]]; then
    [ $(stat -f %m "$ZIP") -gt $(stat -f %m "$DIR") ]
  else
    [ $(stat -c %Y "$ZIP") -gt $(stat -c %Y "$DIR") ]
  fi
}

run_app() {
  # Check arguments
  if [ $# -lt 2 ]; then
    echo "Usage: run_app <app-zip> <command...>"
    return 1
  fi

  local APP_ZIP="$1"
  shift  # Remove first argument

  # Setup paths
  local DEST_DIR="./.app_tmp"
  local APP_DIR="$DEST_DIR/app"

  # Extract if zip is newer than directory
  if is_newer "$APP_ZIP" "$APP_DIR"; then
    mkdir -p "$DEST_DIR"

    # Safe removal: check that APP_DIR is not empty and contains expected path
    if [[ -n "$APP_DIR" && "$APP_DIR" == *".app_tmp/app" ]]; then
      rm -rf "$APP_DIR"
    else
      echo "Error: Unexpected app directory path: $APP_DIR"
      return 1
    fi

    unzip -q "$APP_ZIP" -d "$DEST_DIR"
  fi

  cd "$APP_DIR"

  # Setup environment
  local PYTHON_VERSION=$(cat config/python_version.txt)
  local VENV_PATH=".venv"

  if [ ! -d "$VENV_PATH" ]; then
    uv venv -p "$PYTHON_VERSION" "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    uv pip install --requirement pylock.toml
    uv pip install --offline --no-deps package/*.whl
  else
    source "$VENV_PATH/bin/activate"
  fi

  # Run the command
  exec "$@"
}
