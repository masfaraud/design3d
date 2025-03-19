#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to show design3d capabilities on extrusions
"""

import math

from design3d.models import casing
from design3d.primitives3d import Block

bottom, sides, belt = casing.primitives

bbox = casing.bounding_box

assert bbox.zmin == -0.005
assert math.isclose(bbox.xmax, 0.34067, abs_tol=1e-5)

box = Block.from_bounding_box(bbox)
box.alpha = 0.3
casing.primitives.append(box)
casing.babylonjs()

casing.to_step('casing')
casing.to_stl('casing')

