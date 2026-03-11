import torch
import torch.utils.data
import torch.nn.functional as F
import sys
import os
import json
from pathlib import Path
import numpy as np
import argparse
import math

# Add src to sys.path to ensure lerobot is importable
current_dir = Path(__file__).parent
sys.path.append(str(current_dir / "src"))

from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.policies.factory import make_policy, make_pre_post_processors
from lerobot.policies.pretrained import PreTrainedPolicy
from lerobot.configs.policies import PreTrainedConfig
from lerobot.utils.constants import ACTION, OBS_STATE
from huggingface_hub import hf_hub_download

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy-path", type=str, required=True, help="Path to the pretrained model folder")
    parser.add_argument("--repo-id", type=str, required=True, help="Hugging Face repo ID of the dataset")
    parser.add_argument("--output-dir", type=str, default="InferenceMetrics", help="Directory to save the metrics")
    parser.add_argument("--episode", type=int, default=0, help="Episode index to sample from")
    parser.add_argument("--start-timestamp", type=float, default=9.1, help="Starting time in seconds")
    parser.add_argument("--total-steps", type=int, default=50, help="Number of simulation steps")
    parser.add_argument("--g-threshold", type=float, default=0.7, help="Async queue threshold")
    parser.add_argument("--latency-steps", type=int, default=5, help="Simulation of network/GPU delay")
    parser.add_argument("--m-decay", type=float, default=0.01, help="Temporal ensembling decay constant")
    parser.add_argument("--num-samples", type=int, default=100, help="Number of full async trajectories to simulate")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # 1. Detect Remote vs Local and Load rename_map
    policy_id = args.policy_path
    is_local = Path(policy_id).exists()
    rename_map = {}
    
    if is_local:
        train_config_path = Path(policy_id) / "train_config.json"
        if train_config_path.exists():
            with open(train_config_path, "r") as f:
                train_cfg = json.load(f)
                rename_map = train_cfg.get("rename_map", {})
    else:
        print(f"Policy path not found locally. Attempting to fetch metadata from HF Hub: {policy_id}")
        try:
            train_config_path = hf_hub_download(repo_id=policy_id, filename="train_config.json")
            with open(train_config_path, "r") as f:
                train_cfg = json.load(f)
                rename_map = train_cfg.get("rename_map", {})
        except Exception as e:
            print(f"Warning: Could not fetch train_config.json from Hub ({e}). Proceeding without rename_map.")

    print(f"Loading dataset {args.repo_id}...")
    dataset = LeRobotDataset(args.repo_id)
    
    # 2. Setup Policy
    print(f"Loading policy config from {policy_id}...")
    policy_config = PreTrainedConfig.from_pretrained(policy_id)
    policy_config.pretrained_path = policy_id
    policy = make_policy(cfg=policy_config, ds_meta=dataset.meta, rename_map=rename_map)
    policy.eval()
    policy.to(device)

    chunk_size = policy.config.chunk_size

    # 3. Setup Processors
    preprocessor, postprocessor = make_pre_post_processors(
        policy_cfg=policy.config,
        pretrained_path=policy_id,
        dataset_stats=dataset.meta.stats,
        preprocessor_overrides={"rename_observations_processor": {"rename_map": rename_map}}
    )

    # 4. Simulation Helper
    start_frame = int(round(args.start_timestamp * dataset.meta.fps))
    ep_start_idx = dataset.meta.episodes[args.episode]["dataset_from_index"]

    def run_inference(sim_time):
        global_idx = ep_start_idx + start_frame + sim_time
        if global_idx >= dataset.meta.episodes[args.episode]["dataset_to_index"]:
            return None
        
        batch = dataset[global_idx]
        batch = {k: v.unsqueeze(0) if isinstance(v, torch.Tensor) else [v] for k, v in batch.items()}
        for k in batch:
            if isinstance(batch[k], torch.Tensor):
                batch[k] = batch[k].to(device)
        
        with torch.no_grad():
            obs_pre = preprocessor(batch)
            # The stochasticity comes from Flow Matching / Diffusion sampling
            pred_chunk_norm = policy.predict_action_chunk(obs_pre)
            pred_chunk_unnorm = postprocessor(pred_chunk_norm)
            actions = pred_chunk_unnorm[0].cpu().numpy()
        return actions

    # Pre-fetch Ground Truth for comparison
    ground_truth_trajectory = []
    for t in range(args.total_steps):
        gt_idx = ep_start_idx + start_frame + t
        if gt_idx < dataset.meta.episodes[args.episode]["dataset_to_index"]:
            gt_batch = dataset[gt_idx]
            ground_truth_trajectory.append(gt_batch[ACTION].numpy())
        else:
            ground_truth_trajectory.append(ground_truth_trajectory[-1] if ground_truth_trajectory else np.zeros(6))
    ground_truth_trajectory = np.array(ground_truth_trajectory) # (total_steps, action_dim)

    all_sample_errors = [] # Will store mean error per dimension for each of the 100 runs

    print(f"Starting Batch Evaluation (N={args.num_samples}, g={args.g_threshold}, L={args.latency_steps})...")

    for sample_i in range(args.num_samples):
        if (sample_i + 1) % 10 == 0:
            print(f"Simulation {sample_i + 1}/{args.num_samples}...")
        
        active_chunks = []
        executed_trajectory = []
        in_flight_request = None

        # Initial Kickoff
        first_chunk = run_inference(0)
        active_chunks.append({
            "actions": first_chunk,
            "creation_time": 0,
            "arrival_time": 0
        })

        for t in range(args.total_steps):
            # Arrival logic
            if in_flight_request and t >= in_flight_request["arrival_time"]:
                new_chunk_actions = run_inference(in_flight_request["creation_time"])
                if new_chunk_actions is not None:
                    active_chunks.append({
                        "actions": new_chunk_actions,
                        "creation_time": in_flight_request["creation_time"],
                        "arrival_time": in_flight_request["arrival_time"]
                    })
                in_flight_request = None

            # Ensembling logic
            weighted_sum = None
            total_weight = 0.0
            active_chunks = [c for c in active_chunks if c["creation_time"] + chunk_size > t]
            
            for chunk in active_chunks:
                if chunk["arrival_time"] <= t:
                    idx = t - chunk["creation_time"]
                    if 0 <= idx < chunk_size:
                        val = chunk["actions"][idx]
                        k = t - chunk["creation_time"]
                        weight = math.exp(-args.m_decay * k)
                        if weighted_sum is None:
                            weighted_sum = val * weight
                        else:
                            weighted_sum += val * weight
                        total_weight += weight
            
            if weighted_sum is not None:
                executed_action = weighted_sum / total_weight
            else:
                # Fallback: if queue is empty (idle gap), hold the last executed action
                if executed_trajectory:
                    executed_action = executed_trajectory[-1]
                else:
                    executed_action = np.zeros(ground_truth_trajectory.shape[1])
            
            executed_trajectory.append(executed_action)

            # Trigger logic (Constant Trigger assumed)
            if not active_chunks:
                if in_flight_request is None:
                    in_flight_request = {
                        "creation_time": t,
                        "arrival_time": t + args.latency_steps
                    }
            else:
                latest_chunk = active_chunks[-1]
                remaining_in_latest = (latest_chunk["creation_time"] + chunk_size) - t
                if (remaining_in_latest / chunk_size) < args.g_threshold and in_flight_request is None:
                    in_flight_request = {
                        "creation_time": t,
                        "arrival_time": t + args.latency_steps
                    }

        executed_trajectory = np.array(executed_trajectory)
        # Compute Mean Absolute Error for this specific run (over all steps and per dimension)
        # errors shape: (total_steps, action_dim)
        errors = np.abs(executed_trajectory - ground_truth_trajectory)
        # mean_error_per_dim shape: (action_dim,)
        mean_error_per_dim = np.mean(errors, axis=0)
        all_sample_errors.append(mean_error_per_dim)

    # 5. Aggregate and Save
    all_sample_errors = np.array(all_sample_errors) # (N, action_dim)
    final_avg_error = np.mean(all_sample_errors, axis=0)
    final_std_error = np.std(all_sample_errors, axis=0)

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    filename = f"metrics_g{args.g_threshold}.txt"
    file_path = Path(args.output_dir) / filename

    with open(file_path, "w") as f:
        f.write("Asynchronous Inference Evaluation Metrics\n")
        f.write("==========================================\n")
        f.write(f"Policy: {args.policy_path}\n")
        f.write(f"Dataset: {args.repo_id}\n")
        f.write(f"Episode: {args.episode}, Start Timestamp: {args.start_timestamp}\n")
        f.write(f"Number of Independent Runs: {args.num_samples}\n")
        f.write(f"Steps per Run: {args.total_steps}\n")
        f.write(f"g-threshold: {args.g_threshold}\n")
        f.write(f"Latency Steps: {args.latency_steps}\n")
        f.write(f"Decay constant (m): {args.m_decay}\n\n")
        
        f.write("Results (Mean Absolute Error per Sensor/Dimension):\n")
        for i in range(len(final_avg_error)):
            f.write(f"Dimension {i}: Avg Error = {final_avg_error[i]:.6f}, Std Dev = {final_std_error[i]:.6f}\n")

    print(f"Metrics saved to {file_path}")

if __name__ == "__main__":
    main()
