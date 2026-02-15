#!/usr/bin/env python3
import pandas as pd
import argparse
import os

def parquet_to_csv(parquet_path, output_dir="debug_data"):
    if not os.path.exists(parquet_path):
        print(f"Error: File not found at {parquet_path}")
        return

    # Load the parquet file
    print(f"Reading {parquet_path}...")
    try:
        df = pd.read_parquet(parquet_path)
    except Exception as e:
        print(f"Error reading parquet file: {e}")
        return

    # Basic Info
    print(f"Loaded {len(df)} rows and {len(df.columns)} columns.")

    # Create output filename
    base_name = os.path.basename(parquet_path).replace(".parquet", ".csv")
    output_path = os.path.join(output_dir, base_name)
    
    os.makedirs(output_dir, exist_ok=True)

    # Convert complex types (lists/arrays) to strings so CSV can handle them
    print("Converting complex columns for CSV compatibility...")
    for col in df.columns:
        if isinstance(df[col].iloc[0], (list, pd.Series)) or str(df[col].dtype) == 'object':
            df[col] = df[col].apply(lambda x: str(x.tolist()) if hasattr(x, 'tolist') else str(x))

    # Save to CSV
    print(f"Saving to {output_path}...")
    df.to_csv(output_path, index=False)
    print("Done!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a Parquet file to CSV for easy browsing.")
    parser.add_argument("parquet_path", help="Path to the .parquet file")
    parser.add_argument("--output_dir", default="debug_data", help="Directory to save the CSV (default: debug_data)")
    args = parser.parse_args()

    parquet_to_csv(args.parquet_path, args.output_dir)
