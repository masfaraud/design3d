#!/usr/bin/env python3
"""
Parametric 2D profiles: a plate with a hexagonal hole and two slots, extruded.
"""

import math

import design3d as d3d
import design3d.primitives2d as primitives2d
import design3d.primitives3d as primitives3d

outer_profile = primitives2d.RoundedRectangle2D(0.3, 0.2, 0.02)
hexagon = primitives2d.RegularPolygon2D(6, 0.03, angle=math.pi / 6)
slots = [
    primitives2d.Slot2D(0.08, 0.02, center=d3d.Point2D(-0.1, 0.0), angle=0.5 * math.pi),
    primitives2d.Slot2D(0.08, 0.02, center=d3d.Point2D(0.1, 0.0), angle=0.5 * math.pi),
]

plate = primitives3d.ExtrudedProfile(d3d.OXYZ, outer_profile, [hexagon, *slots], 0.01, name="plate")

model = d3d.core.VolumeModel([plate])
model.babylonjs()
