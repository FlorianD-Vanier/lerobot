
import sys
import os
from pathlib import Path

# Ensure src is in path so we can import lerobot
if (Path(__file__).parent / "src").exists():
    sys.path.append(str(Path(__file__).parent / "src"))

from lerobot.robots.finger.finger_robot import FingerRobot, FingerRobotConfig

def calibrate():
    print("====================================")
    print("   Finger Robot Calibration Wizard  ")
    print("====================================")
    
    try:
        # Create default config (points to sts3215 on ACM0)
        config = FingerRobotConfig()
        
        print(f"Connecting to Robot on {config.port}...")
        
        # Instantiate Robot
        # Note: We pass calibrate=False to connect because we want to trigger it manually
        # inside this script to have better control of the UX.
        # But wait, our connect() implementation calls calibrate() automatically if not calibrated.
        # That's fine, we'll let it happen or call it explicitly.
        
        robot = FingerRobot(config)
        robot.connect(calibrate=True)
        
        if robot.is_calibrated:
            print("\nSUCCESS! Calibration completed and saved.")
        else:
            print("\nWARNING: Calibration might not have completed successfully.")
            
    except Exception as e:
        print(f"\nCalibration Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Ensure we disconnect cleanly
        if 'robot' in locals() and robot.is_connected:
            robot.disconnect()

if __name__ == "__main__":
    calibrate()
