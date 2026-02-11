
import sys
import os
from pathlib import Path

# Add src to path
if (Path(__file__).parent / "src").exists():
    sys.path.append(str(Path(__file__).parent / "src"))

from lerobot.datasets.lerobot_dataset import LeRobotDataset

def push_selected_dataset():
    # 1. Configuration
    # The exact folder containing meta/, data/, videos/
    local_dir = Path("data/Clockwise_Counter_datasets/2026-02-11_13-27-48")
    
    # The destination on Hugging Face (Format: username/dataset-name)
    repo_id = "FlorianDVanier/finger_test"
    
    print(f"Loading dataset from: {local_dir.resolve()}")
    
    if not local_dir.exists():
        print(f"Error: Folder {local_dir} does not exist.")
        return

    try:
        # Load the dataset
        # Note: We use the parent of local_dir as root, and its name as repo_id if we want to follow typical structure,
        # but LeRobotDataset is flexible. Loading with the specific folder as root and a custom repo_id is cleanest.
        dataset = LeRobotDataset(repo_id=repo_id, root=local_dir)
        
        print(f"Dataset loaded. Total episodes: {dataset.meta.total_episodes}")
        print(f"Pushing to Hugging Face: https://huggingface.co/datasets/{repo_id}")
        
        # 2. Push to Hub
        dataset.push_to_hub()
        
        print("\nSuccess! Your dataset is now public.")
        
    except Exception as e:
        print(f"Error during push: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    push_selected_dataset()
