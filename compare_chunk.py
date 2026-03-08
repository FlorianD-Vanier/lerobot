import torch
import torch.utils.data
import torch.nn.functional as F
import sys
import os
import json
from pathlib import Path

# Add src to sys.path to ensure lerobot is importable
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "src"))

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.policies.pretrained import PreTrainedPolicy
from lerobot.configs.policies import PreTrainedConfig
import matplotlib.pyplot as plt
import numpy as np
import argparse
import math
from lerobot.utils.constants import ACTION, OBS_STATE

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-path", type=str, required=True, help="Path to the pretrained model folder")
    parser.add_argument("--repo-id", type=str, required=True, help="Hugging Face repo ID of the dataset")
    parser.add_argument("--output-dir", type=str, default="plots", help="Directory to save the plots")
    parser.add_argument("--episode", type=int, default=None, help="Specific episode index to sample from")
    parser.add_argument("--timestamp", type=float, default=None, help="Specific timestamp (in seconds) to sample from")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Load train_config.json to get rename_map
    train_config_path = Path(args.policy_path) / "train_config.json"
    rename_map = {}
    if train_config_path.exists():
        with open(train_config_path, "r") as f:
            train_cfg = json.load(f)
            rename_map = train_cfg.get("rename_map", {})
            print(f"Loaded rename_map: {rename_map}")

    # 2. Load the dataset
    print(f"Loading dataset {args.repo_id}...")
    dataset = LeRobotDataset(args.repo_id)
    
    # 3. Load the policy
    print(f"Loading policy config from {args.policy_path}...")
    policy_config = PreTrainedConfig.from_pretrained(args.policy_path)
    policy_config.pretrained_path = args.policy_path
    
    policy = make_policy(cfg=policy_config, ds_meta=dataset.meta, rename_map=rename_map)
    policy.eval()

    # 4. Configure dataset to return chunks
    chunk_size = policy.config.chunk_size
    dataset.delta_indices = {
        ACTION: list(range(chunk_size)),
        OBS_STATE: [0],
    }

    # 5. Load processors
    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=policy.config,
        pretrained_path=args.policy_path,
        dataset_stats=dataset.meta.stats,
        preprocessor_overrides={"rename_observations_processor": {"rename_map": rename_map}}
    )

    # 6. Fetch Sample
    if args.episode is not None and args.timestamp is not None:
        print(f"Fetching specific sample: Episode {args.episode}, Timestamp {args.timestamp}...")
        # Find global index
        ep_meta = dataset.meta.episodes[args.episode]
        # Calculate frame index within episode
        frame_idx = int(round(args.timestamp * dataset.meta.fps))
        global_idx = ep_meta["dataset_from_index"] + frame_idx
        
        # LeRobotDataset usually supports indexing by absolute index
        batch = dataset[global_idx]
        # Collate into a batch of 1
        batch = {k: v.unsqueeze(0) if isinstance(v, torch.Tensor) else [v] for k, v in batch.items()}
    else:
        print("Fetching a random sample from the dataset...")
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=1, shuffle=True)
        batch = next(iter(dataloader))
    
    ep_idx = batch["episode_index"][0].item()
    timestamp = batch["timestamp"][0, 0].item() if batch["timestamp"].dim() > 1 else batch["timestamp"][0].item()
    print(f"Actual Sample: Episode {ep_idx}, Timestamp {timestamp:.3f}")

    # Check if we are near the end of the episode (to explain the 'constant' tail)
    ep_info = dataset.meta.episodes[ep_idx]
    frames_remaining = ep_info["dataset_to_index"] - (ep_info["dataset_from_index"] + int(round(timestamp * dataset.meta.fps)))
    print(f"Frames remaining in episode: {frames_remaining}")

    # Move batch to device
    for k in batch:
        if isinstance(batch[k], torch.Tensor):
            batch[k] = batch[k].to(device)

    # 6. Model Inference
    print("Running model inference to predict action chunk...")
    with torch.no_grad():
        # Preprocess the observation using the pipeline
        obs_preprocessed = preprocessor(batch)
        
        # predict_action_chunk returns (BS, chunk_size, action_dim)
        predicted_chunk = policy.predict_action_chunk(obs_preprocessed)
        
        # Unnormalize the predicted chunk back to physical units
        unnormalized_out = postprocessor(predicted_chunk)
        # unnormalized_out is a tensor of shape (BS, chunk_size, action_dim)
        predicted_actions = unnormalized_out[0].cpu().numpy() # (chunk_size, action_dim)
        
        # Get target actions (Ground Truth)
        if len(dataset.meta.stats[ACTION]["mean"].shape) > 1:
            action_dim = dataset.meta.stats[ACTION]["mean"].shape[1]
        else:
            action_dim = dataset.meta.stats[ACTION]["mean"].shape[0]
        
        target_actions = batch[ACTION][0, :, :action_dim].cpu().numpy()

    # 7. Plotting
    print(f"Creating plots in {args.output_dir}...")
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    num_dims = action_dim
    fig, axes = plt.subplots(num_dims, 1, figsize=(10, 2 * num_dims), sharex=True)
    if num_dims == 1:
        axes = [axes]
    
    for i in range(num_dims):
        axes[i].plot(target_actions[:, i], label="Expert (Ground Truth)", color="green", linestyle="--", alpha=0.7)
        axes[i].plot(predicted_actions[:, i], label="Predicted", color="blue", linewidth=2)
        axes[i].set_ylabel(f"Dim {i}")
        axes[i].legend()
        axes[i].grid(True, which='both', linestyle='--', alpha=0.5)

    axes[-1].set_xlabel("Timestep in Chunk")
    plt.suptitle(f"smolVLA Prediction vs Expert Chunk\nDataset: {args.repo_id}")
    plt.tight_layout()
    
    save_path = Path(args.output_dir) / "prediction_comparison.png"
    plt.savefig(save_path)
    print(f"Plot saved to {save_path}")

if __name__ == "__main__":
    main()
