#!/usr/bin/env python3
"""
Test inference script for LeRobot using the NLTuan/up-down dataset.
This script demonstrates how to:
1. Load a pretrained policy (SmolVLA).
2. Load a sample observation from the dataset.
3. Run inference to predict actions.
"""

import argparse
import sys
import torch
from pathlib import Path

# Add the src directory to the python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.configs.policies import PreTrainedConfig

import argparse
import csv
import sys
import torch
from pathlib import Path

# Add the src directory to the python path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.configs.policies import PreTrainedConfig

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pretrained-path", type=str, default="outputs/train/2026-01-03/12-12-54_up-down-smolvla/checkpoints/016000/pretrained_model")
    parser.add_argument("--dataset-repo-id", type=str, default="NLTuan/up-down")
    parser.add_argument("--start-index", type=int, default=0, help="Starting frame index in the dataset")
    parser.add_argument("--num-steps", type=int, default=400, help="Number of inference steps to run")
    parser.add_argument("--device", type=str, default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--output-csv", type=str, default="inference_evolution.csv", help="Output CSV file for plotting")
    args = parser.parse_args()

    print(f"Loading policy from: {args.pretrained_path}")
    
    # 1. Load Policy
    cfg = PreTrainedConfig.from_pretrained(args.pretrained_path)
    cfg.device = args.device
    
    # 2. Load Dataset
    print(f"Loading dataset: {args.dataset_repo_id}")
    dataset = LeRobotDataset(args.dataset_repo_id, video_backend="pyav")
    
    # Instantiate the policy
    policy = make_policy(cfg, ds_meta=dataset.meta)
    policy.eval()
    policy.to(args.device)
    
    # Create pre/post processors for normalization
    preprocessor, postprocessor = make_pre_post_processors(cfg, dataset_stats=dataset.meta.stats)
    
    print(f"\n--- Running Inference Test (Start Index: {args.start_index}, Steps: {args.num_steps}) ---")
    
    results = []
    
    for i in range(args.num_steps):
        current_index = args.start_index + i
        if current_index >= len(dataset):
            print("Reached end of dataset.")
            break
            
        item = dataset[current_index]
        
        # Prepare observation
        observation = {k: v.unsqueeze(0).to(args.device) for k, v in item.items() if k.startswith("observation")}
        
        # SmolVLA/VLA models often expect a 'task' string. 
        if "task" not in observation and "task" in item:
             observation["task"] = [item["task"]]
        elif "task" not in observation:
             observation["task"] = ["Up-down arm movement demonstration with dual cameras"] 
        
        # Get ground truth
        gt_action = item["action"]
        gt_state = item["observation.state"]
        timestamp = item["timestamp"].item()
        
        # Run Inference
        with torch.no_grad():
            processed_observation = preprocessor(observation)
            action = policy.select_action(processed_observation)
            unnormalized_action = postprocessor(action)
        
        # SmolVLA/ACT might return a chunk of actions [batch, chunk_size, action_dim]
        if unnormalized_action.ndim == 3:
            pred_action = unnormalized_action[0, 0]
        else:
            pred_action = unnormalized_action[0]
            
        # Store results for CSV
        row = {
            "step": i,
            "dataset_index": current_index,
            "timestamp": timestamp,
        }
        # Add actual states (still just state_1 as requested before, but we can add more if needed)
        row["actual_state_1"] = gt_state[1].item()
        
        # Add actual and predicted actions for 0-5
        for j in range(6):
            row[f"actual_action_{j}"] = gt_action[j].item()
            row[f"predicted_action_{j}"] = pred_action[j].item()
            
        results.append(row)
        
        if i % 50 == 0:
            print(f"Step {i}/{args.num_steps} processed...")

    # Write to CSV
    if results:
        with open(args.output_csv, mode='w', newline='') as csvfile:
            fieldnames = ["step", "dataset_index", "timestamp", "actual_state_1"]
            fieldnames += [f"actual_action_{j}" for j in range(6)]
            fieldnames += [f"predicted_action_{j}" for j in range(6)]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)

    print(f"\nInference test complete! Results saved to '{args.output_csv}'")

if __name__ == "__main__":
    main()
