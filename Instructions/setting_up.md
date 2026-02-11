# Setting Up the Finger Robot

Follow these steps to get the Finger Robot up and running.

## 1. Hardware Connection
1.  **Power:** Plug the battery into the control board.
2.  **Data:** Plug the USB-C cable from the control board to your computer.
3.  **Identify Port:** Ensure you know which port the robot is connected to (usually `/dev/ttyACM0` or `/dev/ttyUSB0` on Linux). You can run `lerobot-find-port` to verify.

## 2. Software Environment
Before running any scripts, you need to activate the virtual environment:

```bash
# Navigate to the project root
cd ~/Work/FingerSetup/lerobot

# Activate the venv
source .venv/bin/activate
```

## 3. Fixing Serial Port Permissions
If you get a `Permission denied` error when trying to talk to the robot, Linux is blocking access to the hardware.

### Quick Fix (Temporary)
This works immediately but resets every time you unplug the robot or restart:
```bash
sudo chmod 666 /dev/ttyACM0
```
*(Replace `/dev/ttyACM0` with your actual port if different)*

### Permanent Fix (Recommended)
This gives your user account permanent permission to use serial devices. You only need to do this once:
1. Run this command:
   ```bash
   sudo usermod -aG dialout $USER
   ```
2. **Log out and log back in** (or restart your computer) for the changes to take effect.
