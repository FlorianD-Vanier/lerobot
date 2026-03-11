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
    parser.add_argument("--output-dir", type=str, default="plots", help="Directory to save the plots")
    parser.add_argument("--episode", type=int, default=0, help="Episode index to sample from")
    parser.add_argument("--start-timestamp", type=float, default=0.0, help="Starting time in seconds")
    parser.add_argument("--total-steps", type=int, default=150, help="Number of simulation steps")
    parser.add_argument("--g-threshold", type=float, default=0.7, help="Async queue threshold")
    parser.add_argument("--latency-steps", type=int, default=5, help="Simulation of network/GPU delay")
    parser.add_argument("--m-decay", type=float, default=0.01, help="Temporal ensembling decay constant")
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
    # Ensure pretrained_path matches what LeRobot expects for subsequent loading
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

    # 4. Global Simulation Parameters
    start_frame = int(round(args.start_timestamp * dataset.meta.fps))
    ep_start_idx = dataset.meta.episodes[args.episode]["dataset_from_index"]
    
    # buffers
    active_chunks = [] # List of {actions: np.array, start_time: int, arrival_time: int}
    executed_trajectory = []
    ground_truth_trajectory = []
    
    in_flight_request = None # {creation_time: int, arrival_time: int, observation_frame: int}

    # Helper to run inference at a specific simulation time t
    def run_inference(sim_time):
        global_idx = ep_start_idx + start_frame + sim_time
        # Boundary check
        if global_idx >= dataset.meta.episodes[args.episode]["dataset_to_index"]:
            return None
        
        batch = dataset[global_idx]
        batch = {k: v.unsqueeze(0) if isinstance(v, torch.Tensor) else [v] for k, v in batch.items()}
        for k in batch:
            if isinstance(batch[k], torch.Tensor):
                batch[k] = batch[k].to(device)
        
        with torch.no_grad():
            obs_pre = preprocessor(batch)
            pred_chunk_norm = policy.predict_action_chunk(obs_pre)
            pred_chunk_unnorm = postprocessor(pred_chunk_norm)
            actions = pred_chunk_unnorm[0].cpu().numpy()
        return actions

    print(f"Starting Asynchronous Simulation (g={args.g_threshold}, L={args.latency_steps})...")

    # Initial Kickoff
    first_chunk = run_inference(0)
    active_chunks.append({
        "actions": first_chunk,
        "creation_time": 0,
        "arrival_time": 0
    })

    # Sim Loop
    for t in range(args.total_steps):
        # 1. Handle arriving chunks
        if in_flight_request and t >= in_flight_request["arrival_time"]:
            new_chunk_actions = run_inference(in_flight_request["creation_time"])
            if new_chunk_actions is not None:
                active_chunks.append({
                    "actions": new_chunk_actions,
                    "creation_time": in_flight_request["creation_time"],
                    "arrival_time": in_flight_request["arrival_time"]
                })
            in_flight_request = None

        # 2. Run Temporal Ensembling for current time t
        # We look for all chunks where (creation_time <= t < creation_time + chunk_size)
        # AND chunk must have arrived (arrival_time <= t)
        
        weighted_sum = None
        total_weight = 0.0
        
        # Cleanup old chunks that are fully expired (all their steps are in the past)
        active_chunks = [c for c in active_chunks if c["creation_time"] + chunk_size > t]
        
        for chunk in active_chunks:
            if chunk["arrival_time"] <= t:
                # Local index within the chunk
                idx = t - chunk["creation_time"]
                if 0 <= idx < chunk_size:
                    val = chunk["actions"][idx]
                    # Weighting formula: exp(-m * k)
                    # k is the age of the chunk relative to the *request* time
                    # k = t - creation_time
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
                # Shape fallback for the very first step
                action_dim = dataset.meta.stats[ACTION]["mean"].shape[-1]
                executed_action = np.zeros(action_dim)

        executed_trajectory.append(executed_action)
        
        # Record Ground Truth for this step
        gt_idx = ep_start_idx + start_frame + t
        if gt_idx < dataset.meta.episodes[args.episode]["dataset_to_index"]:
            gt_batch = dataset[gt_idx]
            ground_truth_trajectory.append(gt_batch[ACTION].numpy())
        else:
            ground_truth_trajectory.append(ground_truth_trajectory[-1] if ground_truth_trajectory else executed_action)

        # 3. Check Async Trigger
        if not active_chunks:
            # If the queue is fully empty, we definitely wait for the in-flight,
            # but if there isn't one, we MUST trigger one immediately.
            if in_flight_request is None:
                in_flight_request = {
                    "creation_time": t,
                    "arrival_time": t + args.latency_steps
                }
        else:
            latest_chunk = active_chunks[-1]
            remaining_in_latest = (latest_chunk["creation_time"] + chunk_size) - t
            
            # If queue is low AND we don't have a request pending
            if (remaining_in_latest / chunk_size) < args.g_threshold and in_flight_request is None:
                in_flight_request = {
                    "creation_time": t,
                    "arrival_time": t + args.latency_steps
                }

    # 5. Plotting
    print(f"Creating plots in {args.output_dir}...")
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    
    executed_trajectory = np.array(executed_trajectory)
    ground_truth_trajectory = np.array(ground_truth_trajectory)
    
    action_dim = executed_trajectory.shape[1]
    fig, axes = plt.subplots(action_dim, 1, figsize=(10, 2 * action_dim), sharex=True)
    if action_dim == 1:
        axes = [axes]
    
    for i in range(action_dim):
        axes[i].plot(ground_truth_trajectory[:, i], label="Expert (Ground Truth)", color="green", linestyle="--", alpha=0.6)
        axes[i].plot(executed_trajectory[:, i], label="Async Executed (Ensembled)", color="red", linewidth=2)
        axes[i].set_ylabel(f"Dim {i}")
        axes[i].legend()
        axes[i].grid(True, which='both', linestyle='--', alpha=0.5)

    axes[-1].set_xlabel("Simulation Steps (t)")
    plt.suptitle(f"smolVLA Asynchronous Inference Simulation\ng={args.g_threshold}, Latency={args.latency_steps}, n={chunk_size}")
    plt.tight_layout()
    
    save_path = Path(args.output_dir) / "async_simulation_comparison.png"
    plt.savefig(save_path)
    print(f"Plot saved to {save_path}")

if __name__ == "__main__":
    main()
