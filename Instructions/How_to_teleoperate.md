# Operating Functions

This guide explains how to use the teleoperation and data recording scripts for the Finger Robot.

## Keyboard Teleoperation

The primary script for controlling the robot manually and recording datasets is `teleop_keyboard.py`.

### Execution Command
```bash
python teleop_keyboard.py --repo-id lerobot/finger_test --speed 150 --webcam 2
```

### Argument: `--repo-id`
- **Required:** Yes.
- **Function:** The name of the dataset. It will be saved in `data/Clockwise_Counter_datasets/<repo-id>` by default (or your specified --root).

### Argument: `--task`
- **Default:** "Move finger continuously"
- **Function:** The language instruction describing the task (e.g., "Rotate finger clockwise").

### Argument: `--speed`
- **Range:** 0 to 200.
- **Function:** This sets the rotation speed of the finger. 150 is a good starting point for responsive control.

### Argument: `--webcam`
- **Default:** 0.
- **Function:** Selects which camera to use.
  - **Laptop Webcam:** Usually `0`.
  - **USB Webcam:** Often `2` or `4` on Linux (odd numbers like `1` or `3` are frequently reserved for metadata).
  - **Try:** If `1` fails, try `2`.
  ```bash
  python teleop_keyboard.py --speed 150 --webcam 2
  ```

### Controls
To control the robot, you **must stay focused on the camera window** that pops up. The script listens for key presses in that window:

- **[p]**: Spin Clockwise (Right).
- **[q]**: Spin Counter-Clockwise (Left).
- **[r]**: **Toggle RECORDING**. Press once to start (status turns red), press again to stop.
- **[SPACE]**: Stop the motor immediately.
- **[ESC]**: Quit the script and disconnect the robot safely.

### Data Recording
When you toggle recording with **[r]**, the script starts saving data to the `data/test_dataset/` folder:
1.  **Images**: JPG frames from the webcam are saved in an `images/` subfolder.
2.  **Telemetry**: A `data.csv` file records:
    - `frame_id`: Sequence number.
    - `timestamp`: Precise time of the capture.
    - `action_velocity`: The command you sent via keyboard.
    - `state_velocity`: The actual speed reported by the motor sensors.

### Tips
- **Camera Focus**: If the robot isn't moving when you press keys, click on the "Finger Robot Teleop" window to make sure it has focus.
- **Stop Command**: If the finger keeps spinning, hit the Spacebar or ESC.
