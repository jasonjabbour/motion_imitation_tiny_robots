# coding=utf-8
# Copyright 2020 The Google Research Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import inspect
import time
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(os.path.dirname(currentdir))
os.sys.path.insert(0, parentdir)


"""Pybullet simulation of a bittle robot."""
import math
import os
import re
import numpy as np
import pybullet as pyb  # pytype: disable=import-error

from motion_imitation.robots import bittle_pose_utils
from motion_imitation.robots import bittle_constants
from motion_imitation.robots import bittle_motor
from motion_imitation.robots import minitaur
from motion_imitation.robots import robot_config
from motion_imitation.envs import locomotion_gym_config

NUM_MOTORS = 8
NUM_LEGS = 4
MOTOR_NAMES = [
    "FR_upper_leg_2_hip_motor_joint",
    "FR_lower_leg_2_upper_leg_joint",
    "FL_upper_leg_2_hip_motor_joint",
    "FL_lower_leg_2_upper_leg_joint",
    "RR_upper_leg_2_hip_motor_joint",
    "RR_lower_leg_2_upper_leg_joint",
    "RL_upper_leg_2_hip_motor_joint",
    "RL_lower_leg_2_upper_leg_joint"
]

INIT_RACK_POSITION = [0, 0, 1]
INIT_POSITION = [0, 0, 0.90]
JOINT_DIRECTIONS = np.array([1, 1, 1, 1, 1, 1, 1, 1])
HIP_JOINT_OFFSET = 0.0
UPPER_LEG_JOINT_OFFSET = 0.0
KNEE_JOINT_OFFSET = 0.0
DOFS_PER_LEG = 2 #one for each servo motor (rotational DF)
JOINT_OFFSETS = np.array(
    [UPPER_LEG_JOINT_OFFSET, KNEE_JOINT_OFFSET] * 4)
PI = math.pi

MAX_MOTOR_ANGLE_CHANGE_PER_STEP = 0.2
#XYZ is this abduction?
_DEFAULT_HIP_POSITIONS = (
    (0.21, -0.1157, 0),
    (0.21, 0.1157, 0),
    (-0.21, -0.1157, 0),
    (-0.21, 0.1157, 0),
)

# ABDUCTION_P_GAIN = 220.0
# ABDUCTION_D_GAIN = 0.3
# HIP_P_GAIN = 220.0
# HIP_D_GAIN = 2.0
# KNEE_P_GAIN = 220.0
# KNEE_D_GAIN = 2.0

# HIP_P_GAIN = 22.00
# HIP_D_GAIN = .20
# KNEE_P_GAIN = 22.00
# KNEE_D_GAIN = .20

# HIP_P_GAIN = 55.00
# HIP_D_GAIN = .5
# KNEE_P_GAIN = 55.00
# KNEE_D_GAIN = .5

HIP_P_GAIN = 2.75
HIP_D_GAIN = .025
KNEE_P_GAIN = 2.75
KNEE_D_GAIN = .025

# Bases on the readings from Bittles's default pose.
INIT_MOTOR_ANGLES = np.array([
    bittle_pose_utils.BITTLE_DEFAULT_HIP_ANGLE,
    bittle_pose_utils.BITTLE_DEFAULT_KNEE_ANGLE
] * NUM_LEGS)

_CHASSIS_NAME_PATTERN = re.compile(r"\w+_chassis_\w+")
_MOTOR_NAME_PATTERN = re.compile(r"\w+_hip_motor_\w+")
_KNEE_NAME_PATTERN = re.compile(r"\w+_lower_leg_\w+")
_TOE_NAME_PATTERN = re.compile(r"jtoe\d*")

URDF_FILENAME = "models/bittle.urdf"

_BODY_B_FIELD_NUMBER = 2
_LINK_A_FIELD_NUMBER = 3

#Change
UPPER_BOUND = 1.5708
LOWER_BOUND = -1.5708


class Bittle(minitaur.Minitaur):
  """A simulation for the Bittle robot."""
  #CHANGE these values (not used)
  # MPC_BODY_MASS = 2.64/9.8 #.27kg
  # MPC_BODY_INERTIA = (0, 0, 0, 0, 0, 0, 0, 0)
  # MPC_BODY_HEIGHT = 0.42 
  ACTION_CONFIG = [
      locomotion_gym_config.ScalarField(name="FR_upper_leg_2_hip_motor_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="FR_lower_leg_2_upper_leg_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="FL_upper_leg_2_hip_motor_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="FL_lower_leg_2_upper_leg_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="RR_upper_leg_2_hip_motor_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="RR_lower_leg_2_upper_leg_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="RL_upper_leg_2_hip_motor_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708),
      locomotion_gym_config.ScalarField(name="RL_lower_leg_2_upper_leg_joint",
                                        upper_bound=1.5708,
                                        lower_bound=-1.5708)
  ]

  def __init__(
      self,
      pybullet_client,
      motor_control_mode,
      urdf_filename=URDF_FILENAME,
      enable_clip_motor_commands=False,
      time_step=0.001,
      action_repeat=33,
      sensors=None,
      control_latency=0.002,
      on_rack=False,
      enable_action_interpolation=True,
      enable_action_filter=False,
      reset_time=-1,
      allow_knee_contact=False,
      dead_zone=False #NEW
  ):
    self._urdf_filename = urdf_filename
    self._allow_knee_contact = allow_knee_contact
    self._enable_clip_motor_commands = enable_clip_motor_commands

    motor_kp = [
        HIP_P_GAIN, KNEE_P_GAIN,
        HIP_P_GAIN, KNEE_P_GAIN, 
        HIP_P_GAIN, KNEE_P_GAIN,
        HIP_P_GAIN, KNEE_P_GAIN
    ]
    motor_kd = [
        HIP_D_GAIN, KNEE_D_GAIN,
        HIP_D_GAIN, KNEE_D_GAIN, 
        HIP_D_GAIN, KNEE_D_GAIN,
        HIP_D_GAIN, KNEE_D_GAIN
    ]

    super(Bittle, self).__init__(
        pybullet_client=pybullet_client,
        time_step=time_step,
        action_repeat=action_repeat,
        num_motors=NUM_MOTORS,
        dofs_per_leg=DOFS_PER_LEG,
        motor_direction=JOINT_DIRECTIONS,
        motor_offset=JOINT_OFFSETS,
        motor_overheat_protection=False,
        motor_control_mode=motor_control_mode,
        motor_model_class=bittle_motor.BittleMotorModel,
        sensors=sensors,
        motor_kp=motor_kp,
        motor_kd=motor_kd,
        control_latency=control_latency,
        on_rack=on_rack,
        enable_action_interpolation=enable_action_interpolation,
        enable_action_filter=enable_action_filter,
        reset_time=reset_time, 
        dead_zone=dead_zone) #NEW

  def _LoadRobotURDF(self):
    bittle_urdf_path = self.GetURDFFile()
    if self._self_collision_enabled:
      self.quadruped = self._pybullet_client.loadURDF(
          bittle_urdf_path,
          self._GetDefaultInitPosition(),
          self._GetDefaultInitOrientation(),
          flags=self._pybullet_client.URDF_USE_SELF_COLLISION)
    else:
      self.quadruped = self._pybullet_client.loadURDF(
          bittle_urdf_path, self._GetDefaultInitPosition(),
          self._GetDefaultInitOrientation())

  def _SettleDownForReset(self, default_motor_angles, reset_time):
    self.ReceiveObservation()

    if reset_time <= 0:
      return

    for _ in range(500):
      self._StepInternal(
          INIT_MOTOR_ANGLES,
          motor_control_mode=robot_config.MotorControlMode.POSITION)
    if default_motor_angles is not None:
      num_steps_to_reset = int(reset_time / self.time_step)
      for _ in range(num_steps_to_reset):
        self._StepInternal(
            default_motor_angles,
            motor_control_mode=robot_config.MotorControlMode.POSITION)

  def GetHipPositionsInBaseFrame(self):
    return _DEFAULT_HIP_POSITIONS

  def GetFootContacts(self):
    all_contacts = self._pybullet_client.getContactPoints(bodyA=self.quadruped)

    contacts = [False, False, False, False]
    for contact in all_contacts:
      # Ignore self contacts
      if contact[_BODY_B_FIELD_NUMBER] == self.quadruped:
        continue
      try:
        toe_link_index = self._foot_link_ids.index(
            contact[_LINK_A_FIELD_NUMBER])
        contacts[toe_link_index] = True
      except ValueError:
        continue

    return contacts

  def ComputeJacobian(self, leg_id):
    """Compute the Jacobian for a given leg."""
    # Because of the default rotation in the Laikago URDF, we need to reorder
    # the rows in the Jacobian matrix.

    #return super(Bittle, self).ComputeJacobian(leg_id)[(2, 0, 1), :]
    #CHANGE rotation of bittle is normal
    return super(Bittle, self).ComputeJacobian(leg_id)


  def ResetPose(self, add_constraint):
    del add_constraint
    for name in self._joint_name_to_id:
      joint_id = self._joint_name_to_id[name]
      self._pybullet_client.setJointMotorControl2(
          bodyIndex=self.quadruped,
          jointIndex=(joint_id),
          controlMode=self._pybullet_client.VELOCITY_CONTROL,
          targetVelocity=0,
          force=0)
    for name, i in zip(MOTOR_NAMES, range(len(MOTOR_NAMES))):
      if "hip_motor_2_chassis_joint" in name:
        angle = INIT_MOTOR_ANGLES[i] + HIP_JOINT_OFFSET
      elif "upper_leg_2_hip_motor_joint" in name:
        angle = INIT_MOTOR_ANGLES[i] + UPPER_LEG_JOINT_OFFSET
      elif "lower_leg_2_upper_leg_joint" in name:
        angle = INIT_MOTOR_ANGLES[i] + KNEE_JOINT_OFFSET
      else:
        raise ValueError("The name %s is not recognized as a motor joint." %
                         name)
      self._pybullet_client.resetJointState(self.quadruped,
                                            self._joint_name_to_id[name],
                                            angle,
                                            targetVelocity=0)

  def GetURDFFile(self):
    return self._urdf_filename

  def _BuildUrdfIds(self):
    """Build the link Ids from its name in the URDF file.

    Raises:
      ValueError: Unknown category of the joint name.
    """
    num_joints = self._pybullet_client.getNumJoints(self.quadruped)
    self._chassis_link_ids = [-1]
    self._leg_link_ids = []
    self._motor_link_ids = []
    self._knee_link_ids = []
    self._foot_link_ids = []

    for i in range(num_joints):
      joint_info = self._pybullet_client.getJointInfo(self.quadruped, i)
      joint_name = joint_info[1].decode("UTF-8")
      joint_id = self._joint_name_to_id[joint_name]
      if _CHASSIS_NAME_PATTERN.match(joint_name):
        self._chassis_link_ids.append(joint_id)
      elif _MOTOR_NAME_PATTERN.match(joint_name):
        self._motor_link_ids.append(joint_id)
      # We either treat the lower leg or the toe as the foot link, depending on
      # the urdf version used.
      elif _KNEE_NAME_PATTERN.match(joint_name):
        self._knee_link_ids.append(joint_id)
      elif _TOE_NAME_PATTERN.match(joint_name):
        self._foot_link_ids.append(joint_id)
      # else:
      #   raise ValueError("Unknown category of joint %s" % joint_name)

    self._leg_link_ids.extend(self._knee_link_ids)
    self._leg_link_ids.extend(self._foot_link_ids)
    if self._allow_knee_contact:
      self._foot_link_ids.extend(self._knee_link_ids)

    self._chassis_link_ids.sort()
    self._motor_link_ids.sort()
    self._foot_link_ids.sort()
    self._leg_link_ids.sort()

  def _GetMotorNames(self):
    return MOTOR_NAMES

  def _GetDefaultInitPosition(self):
    if self._on_rack:
      return INIT_RACK_POSITION
    else:
      return INIT_POSITION

  def _GetDefaultInitOrientation(self):
    # The Laikago URDF assumes the initial pose of heading towards z axis,
    # and belly towards y axis. The following transformation is to transform
    # the Laikago initial orientation to our commonly used orientation: heading
    # towards -x direction, and z axis is the up direction.
    # init_orientation = pyb.getQuaternionFromEuler(
    #     [math.pi / 2.0, 0, math.pi / 2.0])
    #bittle heads in y direciton, change to the x direction
    init_orientation= pyb.getQuaternionFromEuler([0,0, -1.5708])
    return init_orientation

  def GetDefaultInitPosition(self):
    """Get default initial base position."""
    return self._GetDefaultInitPosition()

  def GetDefaultInitOrientation(self):
    """Get default initial base orientation."""
    return self._GetDefaultInitOrientation()

  def GetDefaultInitJointPose(self):
    """Get default initial joint pose."""
    joint_pose = (INIT_MOTOR_ANGLES + JOINT_OFFSETS) * JOINT_DIRECTIONS
    return joint_pose

  def ApplyAction(self, motor_commands, motor_control_mode):
    """Clips and then apply the motor commands using the motor model.

    Args:
      motor_commands: np.array. Can be motor angles, torques, hybrid commands,
        or motor pwms (for Minitaur only).N
      motor_control_mode: A MotorControlMode enum.
    """
    if self._enable_clip_motor_commands:
      motor_commands = self._ClipMotorCommands(motor_commands)

    super(Bittle, self).ApplyAction(motor_commands, motor_control_mode)

  def _ClipMotorCommands(self, motor_commands):
    """Clips motor commands.

    Args:
      motor_commands: np.array. Can be motor angles, torques, hybrid commands,
        or motor pwms (for Minitaur only).

    Returns:
      Clipped motor commands.
    """

    # clamp the motor command by the joint limit, in case weired things happens
    max_angle_change = MAX_MOTOR_ANGLE_CHANGE_PER_STEP
    current_motor_angles = self.GetMotorAngles()
    motor_commands = np.clip(motor_commands,
                             current_motor_angles - max_angle_change,
                             current_motor_angles + max_angle_change)
    return motor_commands

  @classmethod
  def GetConstants(cls):
    del cls
    return bittle_constants
