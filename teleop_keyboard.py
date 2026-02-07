
import sys
import os
import time
import argparse
import cv2
import numpy as np
import csv
from datetime import datetime

sys.path.append(os.path.join(os.getcwd(), "lerobot", "src"))
sys.path.append(os.path.join(os.getcwd(), "lerobot"))

from lerobot.robots.finger.finger_robot import FingerRobot, FingerRobotConfig

def teleop_keyboard():
    parser = argparse.ArgumentParser(description="Keyboard Teleoperation & Data Recording for Finger Robot")
    parser.add_argument("--speed", type=int, default=100, help="Control Speed (0-200)")
    parser.add_argument("--out", type=str, default="data/test_dataset", help="Output directory for recording")
    args = parser.parse_args()
    
    SPEED = min(max(args.speed, 0), 200) # Clamp 0-200
    
    print("========================================")
    print(f"   Keyboard Teleoperation (Speed: {SPEED})   ")
    print("========================================")
    print("Controls:")
    print("  [p] - Spin Clockwise (Right)")
    print("  [q] - Spin Counter-Clockwise (Left)")
    print("  [r] - Toggle RECORDING (Start/Stop)")
    print("  [SPACE] - Stop")
    print("  [ESC] - Quit")
    
    # Create Output Dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_dir = os.path.join(args.out, timestamp)
    images_dir = os.path.join(dataset_dir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
        
    csv_path = os.path.join(dataset_dir, "data.csv")
    csv_file = open(csv_path, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["frame_id", "timestamp", "action_velocity", "state_velocity"]) # Header
    
    config = FingerRobotConfig()
    robot = FingerRobot(config)
    
    is_recording = False
    frame_count = 0
    
    try:
        robot.connect(calibrate=False)
        print("Robot Connected! Focus on the camera window to control.")
        
        while True:
            start_time = time.time()
            
            # 1. Get Observation (Camera + Motor State)
            obs = robot.get_observation()
            
            # 2. Visualize Camera
            img = obs.get("observation.images.webcam")
            if img is not None:
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                
                # Add Overlay Text
                status_text = "RECORDING" if is_recording else "IDLE"
                color = (0, 0, 255) if is_recording else (0, 255, 0)
                cv2.putText(img_bgr, f"Status: {status_text}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                cv2.putText(img_bgr, f"Speed: {SPEED}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 1)
                
                cv2.imshow("Finger Robot Teleop", img_bgr)
            
            # 3. Handle Keyboard Input
            key = cv2.waitKey(20) & 0xFF 
            
            action_val = 0
            
            if key == ord('q'):
                action_val = -SPEED
                #print(f"Action: LEFT ({action_val})")
            elif key == ord('p'):
                action_val = SPEED
                #print(f"Action: RIGHT ({action_val})")
            elif key == ord('r'):
                is_recording = not is_recording
                print(f"Recording State: {is_recording}")
            elif key == 27: # ESC
                print("Exiting...")
                break
            
            # 4. Send Action
            robot.send_action({"finger": action_val})
            
            # 5. Record Data if Active
            if is_recording and img is not None:
                # Save Image
                img_name = f"frame_{frame_count:06d}.jpg"
                img_path = os.path.join(images_dir, img_name)
                # Save RGB as BGR for OpenCV
                cv2.imwrite(img_path, img_bgr)
                
                # Save CSV Row
                state_vel = obs.get("observation.state.finger", 0)
                csv_writer.writerow([frame_count, time.time(), action_val, state_vel])
                
                frame_count += 1
                if frame_count % 30 == 0:
                    print(f"Recorded {frame_count} frames...")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'robot' in locals() and robot.is_connected:
            robot.disconnect()
        if 'csv_file' in locals():
            csv_file.close()
        cv2.destroyAllWindows()
        print(f"Dataset saved to: {dataset_dir}")

if __name__ == "__main__":
    teleop_keyboard()
