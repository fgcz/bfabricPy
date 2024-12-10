#!/bin/bash
set -euxo pipefail
# Parse arguments
TARGET_DIR=$(readlink -f "${1:-./dist}")
TARGET_NAME="${2:-app_runner}"
DOCKER=docker

DEPLOY_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
APP_RUNNER_PROJECT_DIR=$(realpath "$DEPLOY_DIR/..")
BUILDER_IMAGE=local-build_app_runner:0.0.1
$DOCKER build -t $BUILDER_IMAGE "$DEPLOY_DIR/builder"

mkdir -p "$TARGET_DIR"
$DOCKER run \
    --user "$(id -u):$(id -g)" \
    --rm \
    --mount type=bind,source="$APP_RUNNER_PROJECT_DIR",target=/work/app_runner \
    --mount type=bind,source="$DEPLOY_DIR"/build_steps.sh,target=/work/build_steps.sh,readonly \
    --mount type=bind,source="$TARGET_DIR",target=/work/dist \
    --workdir /work/app_runner \
    "$BUILDER_IMAGE" \
    bash /work/build_steps.sh /work/dist "$TARGET_NAME"
