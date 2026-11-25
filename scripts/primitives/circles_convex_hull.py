#!/usr/bin/env python3
"""
Profiles enveloping circles: a connecting rod and a crank web, extruded.
"""

import design3d as d3d
import design3d.primitives2d as primitives2d
import design3d.primitives3d as primitives3d
from design3d.curves import Circle2D
from design3d.wires import Contour2D


def hole(center: d3d.Point2D, radius: float) -> Contour2D:
    return Contour2D.from_circle(Circle2D.from_center_and_radius(center, radius))


# Connecting rod: big end and small end, with their bores
big_end, small_end = d3d.Point2D(0.0, 0.0), d3d.Point2D(0.0, 0.13)
rod_profile = primitives2d.CirclesConvexHull2D([big_end, small_end], [0.03, 0.016])
connecting_rod = primitives3d.ExtrudedProfile(
    d3d.OXYZ, rod_profile, [hole(big_end, 0.021), hole(small_end, 0.01)], 0.02, name="Connecting rod"
)

# Crank web: main journal, crank pin and counterweight; the offset profile is still a hull of circles
main_journal, crank_pin = d3d.Point2D(0.0, 0.0), d3d.Point2D(0.0, 0.045)
web_profile = primitives2d.CirclesConvexHull2D(
    [main_journal, crank_pin, d3d.Point2D(-0.03, -0.02), d3d.Point2D(0.03, -0.02)], [0.03, 0.025, 0.035, 0.035]
)
print(f"Web profile: {len(web_profile.primitives)} edges, area {web_profile.area():.5f} m²")
print(f"Offset web profile: {web_profile.offset(0.005).__class__.__name__}")
crank_web = primitives3d.ExtrudedProfile(
    d3d.OXYZ.translation(d3d.Vector3D(0.15, 0.0, 0.0)), web_profile, [hole(main_journal, 0.022)], 0.016, name="Web"
)

model = d3d.core.VolumeModel([connecting_rod, crank_web])
model.babylonjs()
