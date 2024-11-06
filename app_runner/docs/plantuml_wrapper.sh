#!/bin/bash
set -e

# Configuration
DOCKER="docker"
IMAGE="plantuml/plantuml:1.2024.7"

# Ensure container exists
$DOCKER pull $IMAGE >/dev/null 2>&1

# Read PlantUML input
input=$(cat)

# Check if input is empty
if [ -z "$input" ]; then
    echo "Error: No PlantUML diagram provided via stdin" >&2
    exit 1
fi

# Run PlantUML in pipe mode
echo "$input" | $DOCKER run --rm -i \
    --user "$(id -u):$(id -g)" \
    $IMAGE \
    -pipe -tsvg -charset utf-8
