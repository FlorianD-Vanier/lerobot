
import sys
import os
import time
from pathlib import Path

# Add LeRobot to path
if (Path(__file__).parent / "src").exists():
    sys.path.append(str(Path(__file__).parent / "src"))

from lerobot.robots.finger.finger_robot import FingerRobot, FingerRobotConfig

def test_velocity():
    print("Testing Velocity Mode (Safe Speeds)...")
    config = FingerRobotConfig()
    robot = FingerRobot(config)
    
    try:
        robot.connect(calibrate=False)
        print("Connected.")
        
        # SLOW (50)
        print("Spinning CW (Speed 50)...")
        robot.send_action({"finger": 50})
        time.sleep(2)
        
        print("Stopping...")
        robot.send_action({"finger": 0})
        time.sleep(1)
        
        # SLOW (-50)
        print("Spinning CCW (Speed -50)...")
        robot.send_action({"finger": -50})
        time.sleep(2)

        print("Stopping...")
        robot.send_action({"finger": 0})
        time.sleep(1)

        # MEDIUM (100)
        print("Spinning CW (Speed 100)...")
        robot.send_action({"finger": 100})
        time.sleep(1)
        
        print("Stopping...")
        robot.send_action({"finger": 0})
        time.sleep(1)
        
        print("Test Complete!")
        
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        robot.disconnect()

if __name__ == "__main__":
    test_velocity()
