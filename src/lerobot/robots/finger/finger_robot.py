
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any

import numpy as np

from lerobot.cameras.opencv import OpenCVCamera, OpenCVCameraConfig
from lerobot.motors import MotorCalibration
from lerobot.motors.feetech import FeetechMotorsBus, OperatingMode, TorqueMode
from lerobot.motors.motors_bus import Motor, MotorNormMode
from lerobot.robots.config import RobotConfig
from lerobot.robots.robot import Robot
from lerobot.processor import RobotAction, RobotObservation

logger = logging.getLogger(__name__)

# Safety first!
MAX_VELOCITY_LIMIT = 200  # Feetech unit (~steps/s). Max is ~1000. 200 is 20%.

@dataclass
class FingerRobotConfig(RobotConfig):
    type: str = "finger_setup"
    calibration_dir: Path = Path(".cache/calibration")
    port: str = "/dev/ttyACM0"
    
    # Motors: {name: (id, model)}
    motors: Dict[str, tuple] = field(default_factory=lambda: {
        "finger": (1, "sts3215")
    })

    # Cameras
    cameras: Dict[str, OpenCVCameraConfig] = field(default_factory=lambda: {
        "webcam": OpenCVCameraConfig(index_or_path=0, fps=30, width=640, height=480)
    })
    
    leader_robot_type: str | None = None

class FingerRobot(Robot):
    config_class = FingerRobotConfig
    name = "finger_setup"

    def __init__(self, config: FingerRobotConfig):
        super().__init__(config)
        self.config = config
        
        # Initialize Motor Bus
        motors_dict = {}
        for motor_name, (motor_id, motor_model) in self.config.motors.items():
            motors_dict[motor_name] = Motor(
                id=motor_id, 
                model=motor_model,
                norm_mode=MotorNormMode.RANGE_0_100
            )

        self.robot_arm = FeetechMotorsBus(
            port=self.config.port,
            motors=motors_dict,
            calibration={} 
        )
        
        # Initialize Cameras container
        self._cameras = {}
        for name, cam_config in self.config.cameras.items():
            self._cameras[name] = OpenCVCamera(cam_config)

    @property
    def is_connected(self) -> bool:
        return self.robot_arm.is_connected

    def connect(self, calibrate: bool = True):
        logger.info(f"Connecting to {self.name} (Velocity Mode)...")
        if not self.robot_arm.is_connected:
            self.robot_arm.connect()
        
        for name, cam in self._cameras.items():
            if not cam.is_connected:
                cam.connect()
        
        self.configure()
        self.robot_arm.enable_torque()
        logger.info(f"Connected to {self.name}")

    def disconnect(self):
        if self.robot_arm.is_connected:
            self.stop()
            self.robot_arm.disconnect()
            
        for cam in self._cameras.values():
            if cam.is_connected:
                cam.disconnect()
        logger.info(f"Disconnected from {self.name}")

    def stop(self):
        for motor_name in self.config.motors:
            try:
                self.robot_arm.write("Goal_Velocity", motor_name, 0)
            except:
                pass

    def send_action(self, action: RobotAction) -> RobotAction:
        if isinstance(action, dict):
            for motor_name, value in action.items():
                if motor_name in self.config.motors:
                    # Input: -100 to 100? or -MAX to MAX?
                    # Let's assume user sends raw units for now or we clamp.
                    
                    target_velocity = int(value)
                    
                    # Clamp for safety
                    if target_velocity > MAX_VELOCITY_LIMIT: 
                        target_velocity = MAX_VELOCITY_LIMIT
                    if target_velocity < -MAX_VELOCITY_LIMIT: 
                        target_velocity = -MAX_VELOCITY_LIMIT
                        
                    # IMPORTANT: Just send signed int. Automation handles bit 15.
                    self.robot_arm.write("Goal_Velocity", motor_name, target_velocity)
                    
        return action

    def get_observation(self) -> RobotObservation:
        obs = {}
        for motor_name in self.config.motors:
            try:
                # Read Velocity (Library handles decoding sign too)
                vel = self.robot_arm.read("Present_Velocity", motor_name)
                obs[f"observation.state.{motor_name}"] = float(vel)
            except Exception as e:
                logger.warning(f"Failed to read {motor_name}: {e}")

        for name, cam in self._cameras.items():
             image = cam.read() 
             if image is not None:
                 obs[f"observation.images.{name}"] = image
        return obs

    @property
    def cameras(self) -> Dict[str, Any]:
        return self._cameras

    def configure(self):
        with self.robot_arm.torque_disabled():
            for motor in self.robot_arm.motors:
                try:
                    # 1 = Velocity Mode
                    self.robot_arm.write("Operating_Mode", motor, 1) 
                    self.robot_arm.write("Goal_Velocity", motor, 0)
                except Exception as e:
                    logger.warning(f"Failed to configure {motor}: {e}")

    def calibrate(self):
        logger.info("Calibration skipped (Velocity Mode).")
        pass

    @property
    def is_calibrated(self) -> bool:
        return True

    @property
    def observation_features(self) -> dict:
        features = {}
        for motor_name in self.config.motors:
            features[f"observation.state.{motor_name}"] = float
        for name, cam in self.cameras.items():
             features[f"observation.images.{name}"] = (cam.height, cam.width, 3)
        return features

    @property
    def action_features(self) -> dict:
        features = {}
        for motor_name in self.config.motors:
            features[f"action.{motor_name}"] = float
        return features
