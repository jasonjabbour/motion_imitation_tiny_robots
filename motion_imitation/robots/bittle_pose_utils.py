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

"""Utility functions to calculate Bittles's pose and motor angles."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import attr

#BITTLE_DEFAULT_ABDUCTION_ANGLE = 0
BITTLE_DEFAULT_HIP_ANGLE = 0.52
BITTLE_DEFAULT_KNEE_ANGLE = 0.52


@attr.s
class BittlePose(object):
  """Default pose of the Bittle.

    Leg order:
    0 -> Front Right.
    1 -> Front Left.
    2 -> Rear Right.
    3 -> Rear Left.
  """
  hip_angle_0 = attr.ib(type=float, default=0)
  knee_angle_0 = attr.ib(type=float, default=0)
  hip_angle_1 = attr.ib(type=float, default=0)
  knee_angle_1 = attr.ib(type=float, default=0)
  hip_angle_2 = attr.ib(type=float, default=0)
  knee_angle_2 = attr.ib(type=float, default=0)
  hip_angle_3 = attr.ib(type=float, default=0)
  knee_angle_3 = attr.ib(type=float, default=0)
