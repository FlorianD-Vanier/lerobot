# How to Explore Parquet Files

This document explains how to use the `explore_parquet.py` script to inspect the contents of Parquet files commonly used in LeRobot datasets (metadata, tasks, stats, etc.).

## Purpose

LeRobot uses Parquet for various metadata files because they are compact and efficient. However, they are not human-readable in a text editor. The `explore_parquet.py` script provides a quick way to:
- Check the number of rows and columns.
- See the data types and schema.
- Preview the actual data (first 5 rows).
- Verify task-to-index mappings.

## How to use

Run the script from the root of the repository, passing the path to the Parquet file as an argument:

```bash
python scripts/explore_parquet.py <path_to_parquet_file>
```

### Examples

**To inspect the task instructions:**
```bash
python scripts/explore_parquet.py debug_data/meta/tasks.parquet
```

**To inspect episode metadata:**
```bash
python scripts/explore_parquet.py debug_data/meta/episodes/chunk-000/file-000.parquet
```

**To inspect frame-by-frame data:**
```bash
python scripts/explore_parquet.py debug_data/data/chunk-000/file-000.parquet
```

## Output Sections

- **[Basic Info]**: Shows total rows and columns.
- **[Schema / Column Types]**: Shows the technical data type of each column (e.g., float32, int64, object).
- **[First 5 Rows]**: A preview of the data.
- **[Task Mapping Detection]**: Specifically mentions if the file looks like a LeRobot tasks instruction file.
