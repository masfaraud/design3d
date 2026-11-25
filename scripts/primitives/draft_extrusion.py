#!/usr/bin/env python3
"""
Draft and symmetric extrusions: a molded plate, drafted on both sides of its parting plane.
"""

import math

import design3d as d3d
import design3d.primitives2d as primitives2d
import design3d.primitives3d as primitives3d

outer_profile = primitives2d.RoundedRectangle2D(0.3, 0.2, 0.03)
holes = [
    primitives2d.Slot2D(0.08, 0.03, center=d3d.Point2D(-0.08, 0.0), angle=0.5 * math.pi),
    primitives2d.Slot2D(0.08, 0.03, center=d3d.Point2D(0.08, 0.0), angle=0.5 * math.pi),
]

plate = primitives3d.ExtrudedProfile(
    d3d.OXYZ, outer_profile, holes, 0.04, draft_angle=math.radians(5), symmetric=True, name="molded plate"
)

model = d3d.core.VolumeModel([plate])
model.babylonjs()
