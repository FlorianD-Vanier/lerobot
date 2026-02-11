import sys
import os
import time
import argparse
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

# Add LeRobot to path
if (Path(__file__).parent / "src").exists():
    sys.path.append(str(Path(__file__).parent / "src"))

from lerobot.robots.finger.finger_robot import FingerRobot, FingerRobotConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset

def teleop_keyboard():
    parser = argparse.ArgumentParser(description="Keyboard Teleoperation & Data Recording for Finger Robot")
    parser.add_argument("--repo-id", type=str, required=True, help="Dataset identifier (e.g. lerobot/finger_test)")
    parser.add_argument("--speed", type=int, default=100, help="Control Speed (0-200)")
    parser.add_argument("--webcam", type=int, default=0, help="Camera Index (default: 0)")
    parser.add_argument("--fps", type=int, default=30, help="Recording FPS (default: 30)")
    parser.add_argument("--root", type=str, default="data/Clockwise_Counter_datasets", help="Root directory for dataset storage")
    parser.add_argument("--task", type=str, default="Move finger continuously", help="Language instruction for the task")
    
    args = parser.parse_args()
    
    SPEED = min(max(args.speed, 0), 200) # Clamp 0-200
    FPS = args.fps
    TASK_DESCRIPTION = args.task
    
    print("========================================")
    print(f"   Keyboard Teleoperation (Speed: {SPEED})   ")
    print(f"   Dataset: {args.repo_id} (FPS: {FPS})      ")
    print(f"   Task: {TASK_DESCRIPTION}                  ")
    print("========================================")
    print("Controls:")
    print("  [p] - Spin Clockwise (Right)")
    print("  [q] - Spin Counter-Clockwise (Left)")
    print("  [r] - Toggle RECORDING (Start/Stop)")
    print("  [SPACE] - Stop")
    print("  [ESC] - Quit")
    
    # 1. Initialize Robot
    config = FingerRobotConfig()
    config.cameras["webcam"].index_or_path = args.webcam
    config.cameras["webcam"].fps = FPS
    robot = FingerRobot(config)
    
    # 2. Define Dataset Features
    # We need to explicitly define what we are recording
    features = {
        "observation.state.finger": {
            "dtype": "float32",
            "shape": (1,),
            "names": ["velocity"]
        },
        "action.finger": {
            "dtype": "float32",
            "shape": (1,),
            "names": ["velocity"]
        },
        "observation.images.webcam": {
            "dtype": "video",
            "shape": (480, 640, 3), # H, W, C
            "names": ["height", "width", "channel"]
        }
    }

    # 3. Create or Load Dataset
    # Treat --root as the base directory, so we append the repo_id to it.
    # e.g. data/Clockwise_Counter_datasets/lerobot/finger_test
    if args.root is not None:
        dataset_root = Path(args.root) / args.repo_id
    else:
        # Default behavior of LeRobotDataset is ~/.cache/huggingface/lerobot/<repo_id>
        # We can pass None to let it handle it, or construct it ourselves.
        dataset_root = None
        
    # Check if dataset already exists at that location
    # Note: If dataset_root is None, we need to resolve it to check existence, 
    # but LeRobotDataset handles resolution internally. 
    # Simpler: Try to load, if fails, create.
    
    import shutil
    try:
        if dataset_root and dataset_root.exists():
             print(f"Loading existing dataset properties from {dataset_root}")
             dataset = LeRobotDataset(
                repo_id=args.repo_id,
                root=dataset_root
             )
        else:
             print(f"Creating new dataset at {dataset_root if dataset_root else 'default cache'}")
             dataset = LeRobotDataset.create(
                repo_id=args.repo_id,
                fps=FPS,
                root=dataset_root,
                features=features,
                robot_type="finger_robot",
                use_videos=True
            )
    except Exception as e:
        # If loading fails (e.g. empty dir or corrupt), create a new timestamped dataset to preserve data
        print(f"Load failed ({e}). Creating new dataset in timestamped subdirectory...")
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if args.root:
            new_root = Path(args.root) / timestamp
        else:
            new_root = Path.home() / ".cache/huggingface/lerobot" / timestamp
            
        print(f"New dataset root: {new_root / args.repo_id}")
            
        dataset = LeRobotDataset.create(
                repo_id=args.repo_id,
                fps=FPS,
                root=new_root,
                features=features,
                robot_type="finger_robot",
                use_videos=True
            )
            
    is_recording = False
    
    # Check if dataset.meta.total_episodes is available, otherwise default to 0
    if hasattr(dataset, "meta") and dataset.meta is not None:
         episode_index = dataset.meta.total_episodes
    else:
         episode_index = 0
    
    try:
        robot.connect(calibrate=False)
        print("Robot Connected! Focus on the camera window to control.")
        
        while True:
            start_loop_time = time.perf_counter()
            
            # 1. Get Observation (Camera + Motor State)
            obs = robot.get_observation()
            
            # 2. Visualize Camera
            img = obs.get("observation.images.webcam")
            if img is not None:
                # Convert RGB to BGR for OpenCV display
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                # Add Overlay Text
                status_text = "RECORDING" if is_recording else "IDLE"
                color = (0, 0, 255) if is_recording else (0, 255, 0)
                cv2.putText(img_bgr, f"Status: {status_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(img_bgr, f"Speed: {SPEED}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                
                cv2.imshow("Finger Robot Teleop", img_bgr)
            
            # 3. Handle Keyboard Input
            key = cv2.waitKey(1) & 0xFF 
            
            action_val = 0
            
            if key == ord('q'):
                action_val = -SPEED
            elif key == ord('p'):
                action_val = SPEED
            elif key == ord('r'):
                # Toggle Recording Logic
                if not is_recording:
                    print(f"Started Recording Episode {episode_index}")
                    is_recording = True
                else:
                    print(f"Stopped Recording Episode {episode_index}")
                    is_recording = False
                    dataset.save_episode()
                    episode_index += 1
                    
            elif key == 27: # ESC
                print("Exiting...")
                if is_recording:
                     # Save partial episode if quitting while recording
                    print(f"Saving final episode {episode_index}")
                    dataset.save_episode()
                break
            
            # 4. Send Action
            robot.send_action({"finger": action_val})
            
            # 5. Record Data if Active
            if is_recording:
                # Prepare frame for dataset
                frame = {
                    "observation.state.finger": np.array([obs["observation.state.finger"]], dtype=np.float32),
                    "observation.images.webcam": obs["observation.images.webcam"],
                    "action.finger": np.array([action_val], dtype=np.float32),
                    "task": TASK_DESCRIPTION
                }
                dataset.add_frame(frame)

            # 6. Maintain Loop Rate (FPS)
            dt = time.perf_counter() - start_loop_time
            sleep_time = max(0, (1.0 / FPS) - dt)
            if sleep_time > 0:
                time.sleep(sleep_time)
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'robot' in locals() and robot.is_connected:
            robot.disconnect()
        
        # Finalize dataset (encode videos, save stats)
        if 'dataset' in locals():
            print("Finalizing dataset...")
            dataset.finalize()
        
        cv2.destroyAllWindows()
        print(f"Dataset saved to: {dataset.root}")

if __name__ == "__main__":
    teleop_keyboard()
