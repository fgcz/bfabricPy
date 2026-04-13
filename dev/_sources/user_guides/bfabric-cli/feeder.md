# Feeder

The `bfabric-cli feeder` command provides feeder operations, primarily for creating importresources from files.

## Overview

```bash
bfabric-cli feeder --help
```

Available subcommands:

| Subcommand | Purpose |
| ----------------------- | --------------------------------------------- |
| `create-importresource` | Create importresources for files in a storage |

______________________________________________________________________

## Creating Importresources

Create importresources for one or more files in a B-Fabric storage.

### Basic Usage

```bash
bfabric-cli feeder create-importresource [STORAGE_ID] [FILES]...
```

### Parameters

| Parameter | Required | Description |
| ------------ | -------- | ---------------------------------------------------- |
| `storage_id` | Yes | ID of the target storage |
| `files` | Yes | One or more file paths to create importresources for |

### Examples

**Create a single importresource:**

```bash
bfabric-cli feeder create-importresource 1 /path/to/data/file.raw
```

**Create importresources for multiple files:**

```bash
bfabric-cli feeder create-importresource 1 \
    /path/to/data/file1.raw \
    /path/to/data/file2.raw \
    /path/to/data/file3.raw
```

**Use glob pattern for multiple files:**

```bash
bfabric-cli feeder create-importresource 1 /path/to/data/*.raw
```

### What It Does

The command:

1. **Validates files** - Checks that the specified files exist
2. **Parses file paths** - Analyzes the path structure using the storage's path convention
3. **Computes file metadata** - Calculates MD5 checksum, file size, file date
4. **Creates importresources** - Creates importresource entities in B-Fabric for each file

### Path Convention (CompMS)

For CompMS (Mass Spectrometry) data, the command uses the `PathConventionCompMS` parser, which expects files to follow a specific directory structure:

```
/storage_root/
    ├── application_name/
    │   ├── container_id/
    │   │   ├── sample_id/
    │   │   │   └── file.raw
```

The parser extracts:

- **Application name** - From the directory name
- **Container ID** - From the container directory
- **Sample ID** - Optional, if present
- **Relative path** - Path relative to the storage root

### Output

The command provides feedback on:

- **Successful creations**: "Importresource X created for file /path/to/file.raw"
- **Updates**: "Importresource X updated for file /path/to/file.raw" (if an importresource already exists)
- **Errors**: "Application Y not found in B-Fabric. Skipping file /path/to/file.raw"

______________________________________________________________________

## Workflow Examples

### Initial Data Ingestion

```bash
# 1. First, verify the storage exists
bfabric-cli api read storage id 1

# 2. Create importresources for new files
bfabric-cli feeder create-importresource 1 /data/2025-01/*.raw
```

### Monitoring File Addition

```bash
# Create a script to monitor for new files
#!/bin/bash
# check_new_files.sh
STORAGE_ID=1
DATA_DIR="/data/incoming"

find "$DATA_DIR" -name "*.raw" -type f | while read file; do
    echo "Processing $file..."
    bfabric-cli feeder create-importresource $STORAGE_ID "$file"
done
```

### Batch Processing Multiple Storages

```bash
# Process files across multiple storages
for storage_id in 1 2 3; do
    bfabric-cli feeder create-importresource $storage_id /data/storage_$storage_id/*.raw
done
```

______________________________________________________________________

## Finding Storage Information

Before creating importresources, verify your storage configuration:

### List All Storages

```bash
bfabric-cli api read storage --limit 20
```

### Show Specific Storage

```bash
bfabric-cli api read storage id 1
```

### Check Storage Path Convention

The storage information will show:

- Storage ID and name
- Base URL/path
- Path convention type (e.g., CompMS)

______________________________________________________________________

## Working with Importresources

After creating importresources, you can work with them:

### List Importresources

```bash
# List all importresources
bfabric-cli api read importresource --limit 50

# Filter by storage
bfabric-cli api read importresource storageid 1

# Filter by date
bfabric-cli api read importresource createdafter 2024-12-01 --limit 20
```

### Check Importresource Details

```bash
# Show specific importresource
bfabric-cli api read importresource id 12345
```

______________________________________________________________________

## Tips and Best Practices

### Verify Files Before Processing

```bash
# Check files exist before creating importresources
ls -lh /data/incoming/*.raw

# Verify file integrity
md5sum /data/incoming/*.raw
```

### Use Absolute Paths

```bash
# Use absolute paths to avoid ambiguity
bfabric-cli feeder create-importresource 1 /full/path/to/data/file.raw
```

### Process in Batches

```bash
# For large numbers of files, process in batches
find /data/incoming -name "*.raw" -type f | head -100 | while read file; do
    bfabric-cli feeder create-importresource 1 "$file"
done
```

### Monitor for Errors

```bash
# Capture and review errors
bfabric-cli feeder create-importresource 1 /data/*.raw 2> errors.log

# Review any failures
grep "error\|Error\|ERROR" errors.log
```

### Test on Small Batch First

```bash
# Test with a few files before processing everything
bfabric-cli feeder create-importresource 1 /data/test/*.raw

# If successful, process the full batch
bfabric-cli feeder create-importresource 1 /data/production/*.raw
```

______________________________________________________________________

## Common Issues

### Storage Not Found

**Error**: Storage with ID X not found

**Solution**: Verify the storage exists:

```bash
bfabric-cli api read storage id <storage-id>
```

### Files Do Not Exist

**Error**: Files /path/to/file1.raw, /path/to/file2.raw do not exist

**Solution**: Check file paths and permissions:

```bash
ls -la /path/to/
```

### Application Not Found

**Error**: Application X not found in B-Fabric. Skipping file /path/to/file.raw

**Solution**: The application derived from the path doesn't exist in B-Fabric. Options:

1. Create the application in B-Fabric
2. Rename the directory to match an existing application
3. Verify the path convention is correct

```bash
# Check available applications
bfabric-cli api read application
```

### Path Convention Mismatch

**Error**: Files don't follow the expected path structure

**Solution**: Ensure files are organized according to the storage's path convention:

```bash
# Check storage configuration
bfabric-cli api read storage id <storage-id>

# Verify file structure
tree /data/
```

______________________________________________________________________

## Integration with Data Ingestion Workflows

The feeder command is typically used as part of a larger data ingestion pipeline:

1. **File Transfer**: Data is transferred to the storage location
2. **Validation**: File integrity is verified (checksums, sizes)
3. **Importresource Creation**: Feeder command creates importresources
4. **Import Process**: B-Fabric imports the data based on importresources
5. **Sample Creation**: Associated samples are created/updated
6. **Analysis**: Data becomes available for analysis

### Example Ingestion Pipeline

```bash
#!/bin/bash
# ingest_data.sh

STORAGE_ID=1
SOURCE_DIR="/data/incoming"
PROCESSED_DIR="/data/processed"

# 1. Validate files
echo "Validating files..."
for file in "$SOURCE_DIR"/*.raw; do
    if [ ! -f "$file" ]; then
        echo "Error: $file does not exist"
        exit 1
    fi
done

# 2. Create importresources
echo "Creating importresources..."
bfabric-cli feeder create-importresource $STORAGE_ID "$SOURCE_DIR"/*.raw

# 3. Move to processed directory
echo "Moving files to processed..."
mv "$SOURCE_DIR"/*.raw "$PROCESSED_DIR/"

echo "Ingestion complete!"
```

______________________________________________________________________

## See Also

- [API Operations](api_operations) - Generic CRUD operations for working with importresources
- [Storage Information](../../api_reference/entity_types/storage) - Storage entity documentation
- [Python API](../../api_reference/index) - Using bfabric in Python for custom feeder logic
