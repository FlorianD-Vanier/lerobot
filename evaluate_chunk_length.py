import torch
import torch.utils.data
import torch.nn.functional as F
import sys
import os
import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import argparse
import math
import pandas as pd
from tqdm import tqdm

# Add src to sys.path to ensure lerobot is importable
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "src"))

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.configs.policies import PreTrainedConfig
from lerobot.utils.constants import ACTION

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-dir", type=str, required=True, help="Path to the checkpoints directory")
    parser.add_argument("--repo-id", type=str, required=True, help="Hugging Face repo ID of the dataset")
    parser.add_argument("--output-dir", type=str, default="evaluation_results", help="Directory to save the metrics and plots")
    parser.add_argument("--episodes", type=str, default="80-99", help="Episode range to evaluate (e.g., 80-99)")
    parser.add_argument("--eval-length", type=int, default=25, help="Number of actions to execute from each predicted chunk")
    parser.add_argument("--checkpoint", type=str, default=None, help="Specific checkpoint step to evaluate (e.g., '020000'). If not provided, it loops over all.")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Parse Episodes
    if "-" in args.episodes:
        start_ep, end_ep = map(int, args.episodes.split("-"))
        eval_episodes = list(range(start_ep, end_ep + 1))
    else:
        eval_episodes = [int(args.episodes)]

    # 2. Setup Dataset
    print(f"Loading dataset {args.repo_id}...")
    dataset = LeRobotDataset(args.repo_id)

    # 3. Find Checkpoints
    checkpoint_dir = Path(args.checkpoint_dir)
    checkpoints = sorted([d for d in checkpoint_dir.iterdir() if d.is_dir() and d.name.isdigit()])
    
    if args.checkpoint:
        checkpoints = [c for c in checkpoints if c.name == args.checkpoint]
        if not checkpoints:
            print(f"Error: Checkpoint {args.checkpoint} not found in {checkpoint_dir}")
            return

    # Add 'last' if it's a directory (though checking for digit names usually covers numbered checkpoints)
    last_checkpoint = checkpoint_dir / "last"
    if last_checkpoint.exists() and last_checkpoint.is_dir():
        # Usually 'last' is a symlink or a copy, but let's see if we should include it.
        # For a trend plot, digit-named checkpoints are better.
        pass

    results = []

    # 4. Loop over Checkpoints
    for ckpt_path in tqdm(checkpoints, desc="Evaluating Checkpoints"):
        step = int(ckpt_path.name)
        
        # The actual model is usually in a 'pretrained_model' subdirectory
        model_path = ckpt_path / "pretrained_model"
        if not model_path.exists():
            print(f"Warning: {model_path} does not exist. Skipping step {step}.")
            continue

        # Load rename_map if exists
        rename_map = {}
        train_config_path = model_path / "train_config.json"
        if train_config_path.exists():
            with open(train_config_path, "r") as f:
                train_cfg = json.load(f)
                rename_map = train_cfg.get("rename_map", {})

        # Setup Policy
        policy_config = PreTrainedConfig.from_pretrained(str(model_path))
        policy_config.pretrained_path = str(model_path)
        policy = make_policy(cfg=policy_config, ds_meta=dataset.meta, rename_map=rename_map)
        policy.eval()
        policy.to(device)

        preprocessor, postprocessor = make_pre_post_processors(
            policy_cfg=policy.config,
            pretrained_path=str(model_path),
            dataset_stats=dataset.meta.stats,
            preprocessor_overrides={"rename_observations_processor": {"rename_map": rename_map}}
        )

        for ep_idx in eval_episodes:
            if ep_idx >= len(dataset.meta.episodes):
                print(f"Warning: Episode {ep_idx} out of range for dataset. Skipping.")
                continue

            ep_info = dataset.meta.episodes[ep_idx]
            start_index = ep_info["dataset_from_index"]
            end_index = ep_info["dataset_to_index"]

            t = 0
            ep_len = end_index - start_index
            ep_total_mse = 0.0
            ep_total_count = 0
            
            while t < ep_len:
                global_idx = start_index + t
                
                # Boundary check - if we are at the very end, stop
                if global_idx >= end_index:
                    break

                batch = dataset[global_idx]
                # Prepare batch
                batch = {k: v.unsqueeze(0) if isinstance(v, torch.Tensor) else [v] for k, v in batch.items()}
                for k in batch:
                    if isinstance(batch[k], torch.Tensor):
                        batch[k] = batch[k].to(device)
                
                with torch.no_grad():
                    obs_pre = preprocessor(batch)
                    pred_chunk_norm = policy.predict_action_chunk(obs_pre)
                    pred_chunk_unnorm = postprocessor(pred_chunk_norm)
                    # actions shape: (1, chunk_size, action_dim)
                    actions = pred_chunk_unnorm[0].cpu().numpy()

                # How many actions to actually take?
                # Use args.eval_length, but don't go past chunk size or episode end
                num_to_take = min(args.eval_length, actions.shape[0], ep_len - t)
                
                # Compare with ground truth
                executed_slice = actions[:num_to_take]
                
                # Get ground truth for these steps
                gt_slice = []
                for i in range(num_to_take):
                    gt_idx = global_idx + i
                    if gt_idx < end_index:
                        gt_batch = dataset[gt_idx]
                        gt_slice.append(gt_batch[ACTION].numpy())
                    else:
                        # Should not happen with num_to_take logic
                        break
                
                gt_slice = np.array(gt_slice)
                
                # Compute MSE for this slice
                mse = np.mean((executed_slice - gt_slice) ** 2)
                ep_total_mse += mse * num_to_take
                ep_total_count += num_to_take
                
                # Advance t
                t += num_to_take

            ep_avg_mse = ep_total_mse / ep_total_count if ep_total_count > 0 else 0
            results.append({"step": step, "episode_index": ep_idx, "val_loss": ep_avg_mse})
            print(f"Checkpoint {step}, Episode {ep_idx}: MSE = {ep_avg_mse:.6f}")

    # 5. Save Results
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df = pd.DataFrame(results)
    csv_path = output_dir / "metrics.csv"
    df.to_csv(csv_path, index=False)
    print(f"Results saved to {csv_path}")

    # 6. Plot Results
    # We will compute the mean val_loss across episodes for the plot
    if not df.empty:
        df_mean = df.groupby("step")["val_loss"].mean().reset_index()
        
        plt.figure(figsize=(10, 6))
        plt.plot(df_mean["step"], df_mean["val_loss"], marker='o', linestyle='-', color='b')
        plt.title(f"Mean Validation MSE vs Training Step\n(Execution Length: {args.eval_length})")
        plt.xlabel("Training Step")
        plt.ylabel("Mean Squared Error (MSE)")
        plt.grid(True, which='both', linestyle='--', alpha=0.5)
        
        plot_path = output_dir / "metrics.png"
        plt.savefig(plot_path)
        print(f"Plot saved to {plot_path}")
    else:
        print("No results to plot.")

if __name__ == "__main__":
    main()
