# Datasets

The `bfabric-cli dataset` command provides dataset-specific operations including viewing, downloading, and uploading datasets.

## Overview

```bash
bfabric-cli dataset --help
```

Available subcommands:

| Subcommand | Purpose               |
| ---------- | --------------------- |
| `show`     | View dataset details  |
| `download` | Download dataset data |
| `upload`   | Upload new datasets   |

______________________________________________________________________

## Showing Datasets

View detailed information about a dataset.

### Basic Usage

```bash
bfabric-cli dataset show [DATASET_ID] [OPTIONS]
```

### Parameters

| Parameter    | Required | Description                                                         |
| ------------ | -------- | ------------------------------------------------------------------- |
| `dataset_id` | Yes      | ID of the dataset to view                                           |
| `--format`   | No       | Output format: `json`, `yaml`, `table-rich` (default: `table-rich`) |

### Examples

**Show dataset details:**

```bash
bfabric-cli dataset show 12345
```

**Show as YAML (useful for many columns):**

```bash
bfabric-cli dataset show 12345 --format yaml
```

**Show as JSON:**

```bash
bfabric-cli dataset show 12345 --format json
```

### Output

The output includes:

- Dataset metadata (ID, name, description, etc.)
- Associated workunit
- Container information
- File details
- Creation/modification timestamps

______________________________________________________________________

## Downloading Datasets

Download dataset data to a local file.

### Basic Usage

```bash
bfabric-cli dataset download [DATASET_ID] [OUTPUT_FILE] [OPTIONS]
```

### Parameters

| Parameter     | Required | Description                                     |
| ------------- | -------- | ----------------------------------------------- |
| `dataset_id`  | Yes      | ID of the dataset to download                   |
| `output_file` | Yes      | Local file path for output                      |
| `--format`    | No       | Format for output file: `parquet`, `csv`, `tsv` |

### Examples

**Download as Parquet:**

```bash
bfabric-cli dataset download 12345 my_data.parquet --format parquet
```

**Download as CSV:**

```bash
bfabric-cli dataset download 12345 my_data.csv --format csv
```

**Download as TSV:**

```bash
bfabric-cli dataset download 12345 my_data.tsv --format tsv
```

### Working with Downloaded Data

**Read Parquet file (Python):**

```python
import polars

df = polars.read_parquet("my_data.parquet")
print(df.head())
```

**Read CSV file:**

```python
import pandas as pd

df = pd.read_csv("my_data.csv")
print(df.head())
```

**Read TSV file:**

```python
import pandas as pd

df = pd.read_csv("my_data.tsv", sep="\t")
print(df.head())
```

### Notes

- The file format depends on how the dataset was stored in B-Fabric
- Parquet is recommended for large datasets
- Progress is shown during download

______________________________________________________________________

## Uploading Datasets

Upload new datasets to B-Fabric from local files.

### Basic Usage

```bash
bfabric-cli dataset upload [FORMAT] [INPUT_FILE] [OPTIONS]
```

### Formats

Available upload formats:

| Format  | Command          | Description              |
| ------- | ---------------- | ------------------------ |
| CSV     | `upload csv`     | Upload from CSV file     |
| TSV     | `upload tsv`     | Upload from TSV file     |
| Parquet | `upload parquet` | Upload from Parquet file |

### Common Parameters

| Parameter        | Required | Description                       |
| ---------------- | -------- | --------------------------------- |
| `input_file`     | Yes      | Path to local file to upload      |
| `--container-id` | Yes      | Container ID to attach dataset to |
| `--name`         | No       | Dataset name (default: filename)  |
| `--description`  | No       | Dataset description               |

### Examples

**Upload CSV:**

```bash
bfabric-cli dataset upload csv my_data.csv --container-id 1234
```

**Upload Parquet with metadata:**

```bash
bfabric-cli dataset upload parquet my_data.parquet \
    --container-id 1234 \
    --name "My Dataset" \
    --description "Analysis results from experiment X"
```

**Upload TSV:**

```bash
bfabric-cli dataset upload tsv my_data.tsv --container-id 1234
```

### Upload Subcommands

#### Upload CSV

```bash
bfabric-cli dataset upload csv [INPUT_FILE] [OPTIONS]
```

CSV-specific options:

| Option         | Description                                 |
| -------------- | ------------------------------------------- |
| `--delimiter`  | Column delimiter (default: `,`)             |
| `--has-header` | Whether first row is header (default: true) |

#### Upload Parquet

```bash
bfabric-cli dataset upload parquet [INPUT_FILE] [OPTIONS]
```

Parquet handles data types automatically, no additional options needed.

#### Upload TSV

```bash
bfabric-cli dataset upload tsv [INPUT_FILE] [OPTIONS]
```

TSV-specific options:

| Option         | Description                                 |
| -------------- | ------------------------------------------- |
| `--has-header` | Whether first row is header (default: true) |

### Verifying Upload

After uploading, verify the dataset:

```bash
# Show the new dataset (you'll need the new ID from upload output)
bfabric-cli dataset show <NEW_DATASET_ID>
```

Or check the container in B-Fabric web interface:

```
https://<bfabric-url>/project/show.html?id=<container-id>&tab=datasets
```

### Notes

- Container must exist and you must have write permissions
- File size is limited by B-Fabric configuration
- Upload progress is displayed
- The dataset ID is returned after successful upload

______________________________________________________________________

## Workflow Example

Complete workflow for downloading, processing, and re-uploading:

```bash
# 1. Download dataset
bfabric-cli dataset download 12345 analysis.parquet --format parquet

# 2. Process the data (e.g., with Python or other tools)
# python process_data.py

# 3. Upload the processed dataset
bfabric-cli dataset upload parquet processed.parquet \
    --container-id 6789 \
    --name "Processed Analysis" \
    --description "Processed version of dataset 12345"
```

______________________________________________________________________

## Tips and Best Practices

### Choose the Right Format

- **Parquet**: Best for large datasets, preserves data types, efficient storage
- **CSV**: Universal format, easy to share, but slower and no type info
- **TSV**: Tab-separated, good for tabular data with special characters

### File Size Considerations

```bash
# Check file size before uploading
ls -lh large_file.parquet

# For very large files, consider splitting or using streaming uploads
```

### Naming Conventions

```bash
# Use descriptive names with dates
bfabric-cli dataset upload parquet results_2025-01-20.parquet \
    --container-id 1234 \
    --name "QC Results - 2025-01-20"
```

### Batch Processing

```bash
# Process multiple datasets in a loop
for dataset_id in 12345 12346 12347; do
    bfabric-cli dataset download $dataset_id data_$dataset_id.parquet --format parquet
    # Process data_$dataset_id.parquet
done
```

______________________________________________________________________

## Common Issues

### Upload Fails - Container Not Found

**Error**: `Container with ID X not found`

**Solution**: Verify the container exists and you have access:

```bash
bfabric-cli api read project id <container-id>
```

### Download Fails - Format Not Supported

**Error**: `Dataset format not supported`

**Solution**: Check available formats or use a different format:

```bash
bfabric-cli dataset show <dataset-id>
# Look for format information in the output
```

### Large File Upload Times Out

**Solution**: For very large files, consider:

1. Using a more efficient format (Parquet)
2. Uploading during off-peak hours
3. Contacting B-Fabric admin for size limits

______________________________________________________________________

## See Also

- [API Operations](api_operations.md) - Generic CRUD operations
- [Workunits](workunits.md) - Working with workunits (datasets are often linked to workunits)
- [Python Dataset API](../../api_reference/entity_types/dataset.md) - Using datasets in Python
