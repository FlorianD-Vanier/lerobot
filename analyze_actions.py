import sys
import os
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import torch

# Add src to sys.path to ensure lerobot is importable
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "src"))

try:
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
except ImportError as e:
    print(f"Error importing LeRobotDataset: {e}")
    sys.exit(1)

def main():
    repo_id = "ThavT/red_block_in_orange_box"
    print(f"Loading dataset {repo_id}...")
    
    # We load without images to be fast and memory-efficient
    # download_videos=False ensures we don't grab large video files
    dataset = LeRobotDataset(repo_id, download_videos=False)
    
    total_frames = dataset.meta.total_frames
    print(f"Dataset has {total_frames} frames.")
    
    # Extract actions efficiently
    # LeRobotDataset.hf_dataset is a HuggingFace Dataset object
    # Accessing it this way uses memory mapping
    print("Extracting actions...")
    actions_list = dataset.hf_dataset["action"]
    actions = np.array(actions_list)
    
    # actions shape should be (N, 6)
    print(f"Actions array shape: {actions.shape}")
    
    # Action names from metadata
    feature_info = dataset.meta.features["action"]
    action_names = feature_info.get("names", [f"dim_{i}" for i in range(6)])
    
    # Plotting: 2x3 grid
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    axes = axes.flatten()
    
    # Premium color palette
    colors = ["#FF5F6D", "#FFC371", "#2193b0", "#6dd5ed", "#11998e", "#38ef7d"]
    
    for i in range(min(6, actions.shape[1])):
        ax = axes[i]
        name = action_names[i]
        data = actions[:, i]
        
        # Scalable approach: 100 bins is good for high resolution data
        ax.hist(data, bins=100, color=colors[i % len(colors)], alpha=0.8, edgecolor='none')
        
        # Add stats to title
        mean_val = np.mean(data)
        std_val = np.std(data)
        ax.set_title(f"{name}\n(mean: {mean_val:.3f}, std: {std_val:.3f})", fontsize=12, fontweight='bold')
        
        ax.set_xlabel("Action Value")
        ax.set_ylabel("Count")
        ax.grid(True, linestyle=':', alpha=0.3)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    plt.suptitle(f"Action Distributions for {repo_id}", fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    output_png = "actions_histogram.png"
    plt.savefig(output_png, transparent=False, facecolor='white', bbox_inches='tight')
    print(f"Success! Histogram saved to {output_png}")

if __name__ == "__main__":
    main()
