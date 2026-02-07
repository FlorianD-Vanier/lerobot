# FingerSetup - Wiring Guide

Follow these steps to safely connect your 1-DoF robot hardware.

## Step 1: Communication (Data)
*   **Action:** Plug a **USB-C cable** into the USB-C port of the Waveshare Driver Board.
*   **Destination:** Connect the other end to a USB port on your **Ubuntu machine**.
*   **Result:** This allows the `lerobot` library to send commands to the board. You may see a status LED turn on (indicating logic power).

## Step 2: Servo Connection
*   **Action:** Take the 3-wire cable from your **Feetech STS3215M** servo.
*   **Destination:** Plug it into **any of the two** available 3-pin white headers on the driver board.
*   **Note:** It does not matter which one you choose; they are on the same shared bus. Ensure the connector is oriented correctly (it usually only fits one way).

## Step 3: Power Connection (High Voltage)
*   **Action:** Connect your **7.4V Li-Po battery** to the green screw terminal on the board.
*   **CRITICAL WARNING:** 
    *   **RED wire** must go to **VIN (+)**.
    *   **BLACK wire** must go to **GND (-)**.
    *   Reversing these wires will likely destroy the driver board.
*   **Result:** This provides the necessary voltage and current to drive the servo motor.

## Step 4: Camera
*   **Action:** Plug your **USB Webcam** into a spare USB port on your computer.
*   **Note:** The camera does not plug into the motor driver board; it communicates directly with your computer.

---

### Final Verification
1.  Is the battery securely connected with correct polarity?
2.  Is the USB-C cable connected to the computer?
3.  Is the servo plugged into one of the headers?

If yes, your hardware is ready for software configuration.
