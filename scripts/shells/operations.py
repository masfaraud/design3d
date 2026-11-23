#!/usr/bin/env python3
"""
Goal: call shells methods (point_belongs, volume)
"""

import os
import sys
import time

import design3d as d3d

# The casing model is defined in the casing showcase (run from this script folder)
sys.path.insert(0, os.path.abspath(os.path.join("..", "showcases")))
from casing import casing  # noqa: E402

bottom, sides, belt = casing.primitives

t1 = time.time()
assert not sides.point_inside(d3d.Point3D(0.1, 0.1, 0.1))
t1 = time.time() - t1
