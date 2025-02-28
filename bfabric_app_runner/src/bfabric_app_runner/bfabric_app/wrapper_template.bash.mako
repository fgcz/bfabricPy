#!/bin/bash
set -eo pipefail

# Function to output app version
output_app_version() {
  tee "$1" <<END_APP_DEFINITION
${app_version}
END_APP_DEFINITION
}

# Function to output workunit definition
output_workunit_definition() {
  tee "$1" <<END_WORKUNIT_DEFINITION
${workunit_definition}
END_WORKUNIT_DEFINITION
}

# Return requested definition when asked
if [ "$1" = "--get-definition" ] && [ -n "$2" ]; then
  case "$2" in
    app_version.yml) output_app_version /dev/stdout ;;
    workunit_definition.yml) output_workunit_definition /dev/stdout ;;
    *) echo "Unknown definition: $2" >&2; exit 1 ;;
  esac
  exit 0
fi

# List available definitions
if [ "$1" = "--list-definitions" ]; then
  echo "Available definitions:"
  echo "- app_version.yml"
  echo "- workunit_definition.yml"
  exit 0
fi

# Enable command tracing for the actual execution part
set -x

# Normal execution continues here
echo "Starting job execution..."

# Set workunit as processing
bfabric-cli api update workunit ${workunit_id} status processing --no-confirm

# Extract configuration files
output_app_version app_version.yml >/dev/null
output_workunit_definition workunit_definition.yml >/dev/null

# If logging is configured
%if log_resource_id is not None:
bfabric-cli api update resource ${log_resource_id} status available --no-confirm
%endif

# Execute the command
${command}

exit 0
