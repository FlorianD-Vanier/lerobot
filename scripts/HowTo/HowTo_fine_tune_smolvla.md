# How to Fine-tune smolVLA

This document explains how to fine-tune the `smolVLA` model using the `lerobot_train.py` script and a configuration override file.

## Overview

Fine-tuning `smolVLA` involve updating a pre-trained Vision-Language-Action model on a specific dataset. Because datasets often have different camera names (e.g., `cam_0` vs `camera1`) or require specific video backends, we use a `.json` override file to keep the command simple and reproducible.

## The Training Command

To start the training from the root of the `lerobot` directory:

```bash
PYTHONPATH=src .venv/bin/python src/lerobot/scripts/lerobot_train.py --config_path train_overrides.json
```

## Configuration (`train_overrides.json`)

The override file handles the "pre-flight" complexity so you don't have to type long command-line arguments. Key sections include:

1.  **Dataset**: Specifies the `repo_id` and the `video_backend`. We use `pyav` for maximum compatibility.
2.  **Policy**: 
    - Sets the `pretrained_path` (`lerobot/smolvla_base`).
    - Defines `input_features` to match the number of cameras in the dataset (e.g., mapping to `camera1` and `camera2`).
3.  **Rename Map**: Maps the raw dataset keys (like `observation.images.cam_0`) to the model's expected keys (like `observation.images.camera1`).
4.  **Training Params**: Sets the `batch_size`, total `steps`, and how often to save checkpoints.

## Monitoring

- **Terminal**: Watch for the "loss" values.
- **Logs**: Results are saved to `outputs/train/<date>/<time>_smolvla_red_block_finetune/`.
- **WandB**: Can be enabled by setting `"enable": true` in the json file.

## Common Fixes

- **Out of Memory (OOM)**: Reduce the `batch_size` in `train_overrides.json`.
- **Feature Mismatch**: Update the `rename_map` or `input_features` if using a new dataset with different camera names.
