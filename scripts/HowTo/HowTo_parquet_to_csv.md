# How to Convert Parquet Data to CSV

This document explains how to use the `parquet_to_csv.py` script to convert technical LeRobot data files into readable CSV spreadsheets.

## Purpose

LeRobot stores frame-by-frame data (actions, states, timestamps) in Parquet format. While efficient for training, it's hard to browse. This script converts them to CSV and automatically handles complex data types (like robot joints or floating-point arrays) by turning them into readable strings.

## How to use

Run the script from the root of the repository:

```bash
python scripts/parquet_to_csv.py <path_to_parquet_file>
```

### Example

To convert the main data file for browsing:
```bash
python scripts/parquet_to_csv.py debug_data/data/chunk-000/file-000.parquet
```

## Features

1.  **Complex Type Handling**: Automatically detects array columns (like `action` or `observation.state`) and converts them into string representations (e.g., `"[0.1, -0.2, ...]"`) so you can see all joint values in one Excel/CSV cell.
2.  **Output Location**: By default, it saves the result in the `debug_data/` folder with the same name as the original file (but with a `.csv` extension).
3.  **Broadcasting Compatibility**: Useful for verifying that timestamps, episode indices, and actions align correctly before starting a long training run.
