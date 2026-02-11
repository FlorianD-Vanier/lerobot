import sys
import os
from pathlib import Path
import time

# Ensure src is in path so we can import lerobot
if (Path(__file__).parent / "src").exists():
    sys.path.append(str(Path(__file__).parent / "src"))

from lerobot.motors.feetech.feetech import TorqueMode
from lerobot.motors.feetech import FeetechMotorsBus
from lerobot.motors.motors_bus import Motor, MotorNormMode

def fix_voltage_limit():
    port = "/dev/ttyACM0"
    print(f"Connecting to Feetech Motor on {port} to fix Voltage Limit...")
    
    motors = {
        "finger": Motor(id=1, model="sts3215", norm_mode=MotorNormMode.RANGE_0_100)
    }
    
    bus = FeetechMotorsBus(port=port, motors=motors)
    
    try:
        # Open port manually to avoid connection checks for now
        bus.port_handler.openPort()
        bus.set_baudrate(1_000_000)
        
        # 1. Disable Torque (Required to write to EPROM)
        print("Disabling Torque...")
        # Write 0 to address 40 (Torque_Enable)
        bus._write(40, 1, 1, 0, raise_on_error=False)
        
        # 2. Unlock EPROM writing
        print("Unlocking EPROM...")
        # Write 0 to address 55 (Lock)
        bus._write(55, 1, 1, 0, raise_on_error=False)
        
        # 3. Read current limit just to be sure
        current_limit, _, _ = bus._read(14, 1, 1, raise_on_error=False)
        print(f"Old Max Voltage Limit: {current_limit/10.0}V")
        
        # 4. Write new limit: 8.5V (Value 85)
        new_limit = 85
        print(f"Writing NEW Max Voltage Limit: {new_limit/10.0}V...")
        # Address 14 is Max_Voltage_Limit
        bus._write(14, 1, 1, new_limit, raise_on_error=False)
        
        # 5. Lock EPROM again
        print("Re-locking EPROM...")
        # Write 1 to address 55 (Lock)
        bus._write(55, 1, 1, 1, raise_on_error=False)
        
        # 6. Verify change
        final_limit, _, _ = bus._read(14, 1, 1, raise_on_error=False)
        print(f"VERIFIED New Limit: {final_limit/10.0}V")
        
        if final_limit == new_limit:
            print("SUCCESS! The motor should now work safely with your 8.4V battery.")
        else:
            print("FAILED to update limit.")

    except Exception as e:
        print(f"Error during fix: {e}")
    finally:
        if bus.port_handler.is_open:
            bus.port_handler.closePort()
            print("Port Closed.")

if __name__ == "__main__":
    fix_voltage_limit()
