import sys
import os

# Ensure src is in path so we can import lerobot
sys.path.append(os.path.join(os.getcwd(), "lerobot", "src"))
sys.path.append(os.path.join(os.getcwd(), "lerobot"))

from lerobot.robots.finger.finger_robot import FingerRobot, FingerRobotConfig

def test_robot_instantiation():
    try:
        print("Initializing FingerRobotConfig...")
        config = FingerRobotConfig()
        print(f"Config: {config}")
        
        print("Instantiating FingerRobot...")
        robot = FingerRobot(config)
        print("Robot Object Created Successfully.")
        
        print("Connecting to Robot...")
        robot.connect()
        print("Connected!")
        
        print(f"Is Connected: {robot.is_connected}")
        
        # Quick read test
        obs = robot.get_observation()
        print("Observation Keys:", obs.keys())
        if "observation.state.finger" in obs:
            print(f"Finger Position: {obs['observation.state.finger']}")
        
        print("Disconnecting...")
        robot.disconnect()
        print("Done.")
        
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_robot_instantiation()
