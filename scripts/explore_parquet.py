#!/usr/bin/env python3
import pandas as pd
import argparse
import os

def explore_parquet(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return

    print(f"\n--- Exploring Parquet File: {file_path} ---")
    
    # Load the parquet file
    try:
        df = pd.read_parquet(file_path)
    except Exception as e:
        print(f"Error reading parquet file: {e}")
        return

    # Basic Information
    print("\n[Basic Info]")
    print(f"Number of Rows: {len(df)}")
    print(f"Number of Columns: {len(df.columns)}")
    
    # Schema / Types
    print("\n[Schema / Column Types]")
    print(df.dtypes)

    # First few rows
    print("\n[First 5 Rows]")
    print(df.head())

    # If it looks like a task mapping (index or task_index)
    if 'task_index' in df.columns or df.index.name == 'task':
        print("\n[Task Mapping Detection]")
        # In LeRobot, tasks.parquet often has the task string as the index
        print("This file appears to contain task instructions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Explore the contents of a Parquet file.")
    parser.add_argument("file_path", help="Path to the .parquet file to explore")
    args = parser.parse_args()

    explore_parquet(args.file_path)
