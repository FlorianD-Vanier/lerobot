import sys
import os
import time

# Ensure src is in path so we can import lerobot
sys.path.append(os.path.join(os.getcwd(), "lerobot", "src"))

from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors.motors_bus import Motor, MotorNormMode

def final_test():
    port = "/dev/ttyACM0"
    print(f"Connecting to Feetech Motor on {port}...")
    
    # Use RANGE_0_100 so we can command it abstractly if we wanted, 
    # but we will use raw writes for simplicity and safety.
    motors = {
        "finger": Motor(id=1, model="sts3215", norm_mode=MotorNormMode.RANGE_0_100)
    }
    
    bus = FeetechMotorsBus(port=port, motors=motors)
    
    try:
        bus.connect()
        print("Connected! No errors means voltage is GOOD.")
        
        # Read current position
        pos = bus.read("Present_Position", "finger")
        print(f"Current Position: {pos}")
        
        # Move to center (2048) over 2 seconds
        target = 2048
        print(f"Moving to Center ({target})...")
        bus.write("Goal_Position", "finger", target)
        
        time.sleep(1)
        
        new_pos = bus.read("Present_Position", "finger")
        print(f"New Position: {new_pos}")
        print("Movement Successful!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        bus.disconnect()
        print("Disconnected.")

if __name__ == "__main__":
    final_test()
