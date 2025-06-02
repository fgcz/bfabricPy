# shellcheck disable=SC2016,SC2154
# Determine app runner version (note app.zip provides a more elegant solution for this problem)
get_app_runner_version() {
    uv run -p 3.13 --with "pyyaml==6.0.2" python - "$1" <<'EOF'
import yaml
import sys
import re
from pathlib import Path
yaml_path = Path(sys.argv[1])
version_string = yaml.safe_load(yaml_path.read_text())["bfabric"]["app_runner"]
if re.match(r"^\d+\.\d+\.\d+$", version_string):
    print(f"bfabric-app-runner=={version_string}")
else:
    print(f"bfabric-app-runner@{version_string}")
EOF
}
app_runner_version=$(get_app_runner_version "${app_yaml_path}")

# Run
uv run --with "$app_runner_version" bfabric-app-runner \
    run workunit --app-definition '${app_yaml_path}' --scratch-root '${scratch_root}' --workunit-ref '${workunit_id}'
