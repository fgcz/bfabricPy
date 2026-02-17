# Executables

The `bfabric-cli executable` command provides operations for managing B-Fabric application executables.

## Overview

```bash
bfabric-cli executable --help
```

Available subcommands:

| Subcommand | Purpose |
| ---------- | ------------------------------------- |
| `show` | View executable details |
| `upload` | Upload new executables (experimental) |
| `dump` | Dump executable contents |

______________________________________________________________________

## Showing Executables

View detailed information about an executable.

### Basic Usage

```bash
bfabric-cli executable show [EXECUTABLE_ID]
```

### Parameters

| Parameter | Required | Description |
| --------------- | -------- | ---------------------------- |
| `executable_id` | Yes | ID of the executable to view |

### Examples

**Show executable details:**

```bash
bfabric-cli executable show 12345
```

**View different executable types:**

```bash
# Different executables may have different structures
bfabric-cli executable show 32859
bfabric-cli executable show 33469
```

### Output

The output includes:

- Executable ID and name
- Associated application
- Encoded executable content
- Parameters and configuration
- Creation/modification information

______________________________________________________________________

## Uploading Executables

Upload new executables to B-Fabric from a YAML file.

### Basic Usage

```bash
bfabric-cli executable upload [YAML_FILE] [OPTIONS]
```

### Parameters

| Parameter | Required | Description |
| ----------- | -------- | -------------------------------------------------- |
| `yaml_file` | Yes | Path to YAML file containing executable definition |
| `--force` | No | Force upload even if validation warnings exist |

### Example

**Upload from YAML file:**

```bash
bfabric-cli executable upload my_executable.yml
```

### YAML Format

The YAML file should define the executable structure. A typical format might look like:

```yaml
name: "My Executable"
description: "Description of the executable"
applicationid: 123
# Additional fields as required by the executable type
content: |
  # Executable content here
```

**Note**: The exact YAML structure depends on the executable type and B-Fabric configuration. Refer to existing executables or consult the B-Fabric documentation for the specific format requirements.

### Experimental Status

The upload command is currently experimental and may change in future releases. Use with caution in production environments.

### Verification

After uploading, verify the executable:

```bash
# Show the new executable (you'll need the new ID from upload output)
bfabric-cli executable show <NEW_EXECUTABLE_ID>
```

______________________________________________________________________

## Dumping Executables

Dump the contents of an executable to examine its configuration.

### Basic Usage

```bash
bfabric-cli executable dump [EXECUTABLE_ID]
```

### Parameters

| Parameter | Required | Description |
| --------------- | -------- | ---------------------------- |
| `executable_id` | Yes | ID of the executable to dump |

### Example

**Dump executable contents:**

```bash
bfabric-cli executable dump 12345
```

### Use Cases

The dump command is useful for:

- **Examining executable configuration**: Understand how an existing executable is configured
- **Creating templates**: Dump an existing executable to use as a template for creating new ones
- **Debugging**: Inspect the actual configuration to troubleshoot issues
- **Documentation**: Generate documentation for existing executables

### Output Format

The dumped output shows the internal structure of the executable, including all configuration parameters, encoded content, and metadata.

______________________________________________________________________

## Workflow Example

Complete workflow for examining and creating executables:

```bash
# 1. Show an existing executable
bfabric-cli executable show 32859

# 2. Dump it to use as a template
bfabric-cli executable dump 32859 > template.yml

# 3. Edit the template to create a new executable
# Edit template.yml with your changes

# 4. Upload the new executable
bfabric-cli executable upload new_executable.yml

# 5. Verify the upload
bfabric-cli executable show <NEW_EXECUTABLE_ID>
```

______________________________________________________________________

## Working with Executables

### Finding Executables

Use the generic API to find executables:

```bash
# List all executables
bfabric-cli api read executable --limit 20

# Find executables by name
bfabric-cli api read executable name "My Executable"

# Find executables for a specific application
bfabric-cli api read executable applicationid 123
```

### Filtering Results

```bash
# Show only specific columns
bfabric-cli api read executable --limit 10 \
    --columns id,name,applicationid,description

# Save results for analysis
bfabric-cli api read executable --format json --file executables.json
```

______________________________________________________________________

## Tips and Best Practices

### Use Dump as Template

```bash
# Dump a working executable
bfabric-cli executable dump 32859 > my_template.yml

# Edit and modify the template
vim my_template.yml

# Upload your new version
bfabric-cli executable upload my_template.yml
```

### Test Before Production

```bash
# Test on TEST environment first
BFABRICPY_CONFIG_ENV=TEST bfabric-cli executable upload test_executable.yml

# Verify it works correctly
BFABRICPY_CONFIG_ENV=TEST bfabric-cli executable show <TEST_ID>

# Then upload to PRODUCTION
BFABRICPY_CONFIG_ENV=PRODUCTION bfabric-cli executable upload production_executable.yml
```

### Keep Executable Descriptions Clear

When creating or updating executables, use descriptive names and descriptions:

```yaml
name: "QC Pipeline v2.1"
description: "Quality control pipeline for mass spectrometry data, version 2.1"
```

### Version Your Executables

Include version information in the name:

```yaml
name: "My Analysis Script v1.0"
name: "My Analysis Script v1.1"
name: "My Analysis Script v2.0"
```

______________________________________________________________________

## Common Issues

### Upload Fails - Validation Error

**Error**: Executable validation failed

**Solution**:

1. Check the YAML syntax
2. Verify all required fields are present
3. Ensure data types are correct
4. Check for missing referenced entities (e.g., applicationid)

### Executable Not Found

**Error**: Executable with ID X not found

**Solution**: Verify the executable exists and you have access:

```bash
bfabric-cli api read executable id <executable-id>
```

### Dump Shows Encoded Content

**Observation**: The executable content appears as base64 or other encoding

**Explanation**: Executables are stored in encoded format for transport. This is expected behavior. Use `show` for a more readable representation.

______________________________________________________________________

## See Also

- [API Operations](api_operations) - Generic CRUD operations for finding executables
- [Workunits](workunits) - Executables are used within workunits
- [Python Executable API](../../api_reference/entity_types/executable) - Using executables in Python
