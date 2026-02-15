import os
import pandas as pd
from huggingface_hub import hf_hub_download

REPO_ID = "ThavT/red_block_in_tape"
REPO_TYPE = "dataset"
LOCAL_DIR = "debug_data"
EPISODE_INDEX = 1

os.makedirs(LOCAL_DIR, exist_ok=True)

# 1. Download Data Parquet
print("Downloading data parquet...")
data_path = hf_hub_download(
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    filename="data/chunk-000/file-000.parquet",
    local_dir=LOCAL_DIR
)
print(f"Downloaded data to: {data_path}")

# 2. Inspect Data Parquet
df = pd.read_parquet(data_path)
print("Columns:", df.columns)
episode_df = df[df["episode_index"] == EPISODE_INDEX]
if not episode_df.empty:
    print(f"Found {len(episode_df)} frames for Episode {EPISODE_INDEX}")
    print(episode_df.head())
else:
    print(f"Episode {EPISODE_INDEX} not found in file-000.parquet. It might be in another file.")

# 3. Download Video Files (assuming Episode 1 is in file-000 based on likelihood)
# Note: Ideally we check meta/episodes to map episode_index to file_index, 
# but for now we assume file-000 covers at least the start.
print("Downloading video files...")
video_files = [
    "videos/observation.images.cam_0/chunk-000/file-000.mp4",
    "videos/observation.images.cam_1/chunk-000/file-000.mp4"
]

for vf in video_files:
    path = hf_hub_download(
        repo_id=REPO_ID,
        repo_type=REPO_TYPE,
        filename=vf,
        local_dir=LOCAL_DIR
    )
    print(f"Downloaded video to: {path}")

# 4. Download Tasks Metadata (to check for instructions)
print("Downloading tasks metadata...")
tasks_path = hf_hub_download(
    repo_id=REPO_ID,
    repo_type=REPO_TYPE,
    filename="meta/tasks.parquet",
    local_dir=LOCAL_DIR
)
print(f"Downloaded tasks to: {tasks_path}")
tasks_df = pd.read_parquet(tasks_path)
print("Tasks Parquet Content:")
print(tasks_df)
