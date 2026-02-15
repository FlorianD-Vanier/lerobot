# How to Download and Inspect Dataset Episodes

This document explains how to use the `download_and_inspect.py` script to manually retrieve and examine specific episodes from a LeRobot-formatted dataset on Hugging Face.

## Purpose

LeRobot v3.0 datasets store videos in large "chunks" (back-to-back episodes in one MP4) and metadata in Parquet files. This makes manual inspection difficult because you can't simply download "Episode 5" as a single file.

The `download_and_inspect.py` script simplifies this by:
1.  Downloading the **Parquet data chunk** containing the frame-by-frame metadata.
2.  Checking which **MP4 video chunks** correspond to the episode you want.
3.  Downloading the **Task metadata** to see the natural language instruction.

## How it works

The script uses `huggingface_hub.hf_hub_download` to pull specific files without needing to clone the entire repository.

### Key Components

- **Repository Configuration**: You set the `REPO_ID` (e.g., `ThavT/red_block_in_tape`).
- **Data Inspection**: It uses `pandas` to read the downloaded Parquet files. It filters by `episode_index` to confirm how many frames are available for that specific part of the dataset.
- **Video Retrieval**: It downloads the `chunk-000` video files. Note that because episodes are stored sequentially, one 7-minute video might contain many 20-second episodes.
- **Task Mapping**: It downloads `meta/tasks.parquet` to show which robot command (e.g., "pick up the red block") is associated with the technical `task_index`.

## Usage

1.  Open `scripts/download_and_inspect.py`.
2.  Update `REPO_ID` and `EPISODE_INDEX` as needed.
3.  Run the script:
    ```bash
    python scripts/download_and_inspect.py
    ```
4.  Files will be saved in the `debug_data/` directory.

## File Structure after running

- `debug_data/data/`: Contains the frame metadata (.parquet).
- `debug_data/videos/`: Contains the raw camera feeds (.mp4).
- `debug_data/meta/`: Contains the task/instruction mapping.
