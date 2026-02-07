# FingerSetup - Hardware Specifications

## Component List

### 1. Servo Motor
*   **Model:** Feetech STS3215M
*   **Type:** Serial Bus Servo (Magnetic Encoder, 360°)
*   **Voltage:** 7.4V (Recommended for high torque), works down to ~6V with reduced performance.
*   **Key Specs:** 19kg.cm Stall Torque at 7.4V.
*   **Link:** [STS3215M 7.4V 19kg.cm Magnetic Encoder 360 Serial Bus Servo](https://abra-electronics.com/electromechanical/motors/servo-motors-feetech/sts3215m-7.4v-19kg.cm-magnetic-encoder-360serial-bus-servo.html)

### 2. Motor Driver Board
*   **Model:** Waveshare Serial Bus Servo Driver Board (WAVE-25514)
*   **Function:** Controls serial bus servos via USB (UART).
*   **Input Interface:** USB-C (to computer).
*   **Output Interface:** 3-pin headers for servo connection.
*   **Power Input:** Green screw terminal block (VIN/GND) for external power.
*   **Link:** [Waveshare Serial Bus Servo Driver Board](https://abra-electronics.com/electromechanical/motors/motor-controllers/wave-25514-serial-bus-servo-driver-board.html)

### 3. Power Source (Battery)
*   **Model:** 7.4V 3800mAh 2S LiPo Battery
*   **Voltage:** 7.4V Nominal (8.4V fully charged).
*   **Connector:** Deans (T-Plug) usually.
*   **Connection Plan:** Deans connector -> 2 raw wires -> Green Screw Terminal on Driver Board.
*   **Link:** [7.4V 3800mAh LiPo Battery](https://abra-electronics.com/batteries-holders/batteries-polymer-lithium-ion/bat-lipo-7-4-3800-d-2s-battery-7-4v-3800mah-upgraded-lipo-rechargeable-battery-for-rc-car-boat.html)

### 4. Camera
*   **Model:** USB High Definition Desktop Webcam
*   **Interface:** USB (Standard Type-A usually, might need adapter if using USB-C port only).
*   **Link:** [USB High Definition Desktop Webcam](https://abra-electronics.com/sensors/sensors-light-imaging-en/cam-usb-1-usb-high-definition-desktop-webcam.html)

---

## Wiring & Power Analysis

### Can we power the board via USB-C only?
**Answer: NO.**

*   **Logic vs. Power:** The USB-C port *does* power the "logic" part of the board, which is why the LED turns on. However, a computer USB port only provides 5V and very low current (0.5A - 0.9A).
*   **Motor Requirements:** Your STS3215M servo is designed for **7.4V** and can draw much higher current (up to several Amps) when moving a load.
*   **Risk:** Trying to run the servo off USB power will likely cause the motor to "brown out" (reset) immediately when it tries to move, or it simply won't have any strength. It could also potentially damage your computer's USB port if it tries to draw too much current.

### Recommended Wiring Plan
1.  **Data:** Connect the **Driver Board** to your **Computer** via **USB-C cable** (for communication).
2.  **Power:** Connect your **7.4V LiPo Battery** to the **Green Screw Terminal** on the driver board.
    *   **CRITICAL:** Double-check polarity! Red wire to `+` (VIN), Black wire to `-` (GND). Reversing this will likely fry the board.
3.  **Servo:** Connect the **STS3215M Servo** to one of the **3-pin headers** on the board.
4.  **Camera:** Connect the **Webcam** directly to a **separate USB port** on the computer.

### Notes
*   **Battery Safety:** Ensure the battery is charged using a proper Li-Po balance charger. Never leave Li-Po batteries unattended during charging.
*   **Bridge Function:** The driver board acts as a bridge: it receives low-power data commands from USB and routes high-power from the battery to the servo motors.

