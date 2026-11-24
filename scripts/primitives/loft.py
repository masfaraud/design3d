#!/usr/bin/env python3
"""
Loft examples: a solid interpolating sections, and an open surface interpolating wires.
"""

import math

import design3d
import design3d.primitives2d as primitives2d
import design3d.primitives3d as primitives3d
import design3d.wires as wires
from design3d import shells


def rounded_rectangle(width: float, height: float, radius: float) -> wires.Contour2D:
    """Rounded rectangle centered on the origin: same primitives whatever its dimensions."""
    return primitives2d.ClosedRoundedLineSegments2D(
        [
            design3d.Point2D(-0.5 * width, -0.5 * height),
            design3d.Point2D(0.5 * width, -0.5 * height),
            design3d.Point2D(0.5 * width, 0.5 * height),
            design3d.Point2D(-0.5 * width, 0.5 * height),
        ],
        {0: radius, 1: radius, 2: radius, 3: radius},
    )


# A tapered and bent beam: sections are positioned along a circular path in the XZ plane, the w vector of each frame
# being tangent to the path.
path_radius = 0.5
sections = []
frames = []
for i, (width, height) in enumerate([(0.12, 0.20), (0.10, 0.15), (0.08, 0.10), (0.07, 0.06)]):
    angle = i * math.radians(20)
    origin = design3d.Point3D(path_radius * (1 - math.cos(angle)), 0.0, path_radius * math.sin(angle))
    w = design3d.Vector3D(math.sin(angle), 0.0, math.cos(angle))
    frames.append(design3d.Frame3D(origin, design3d.Y3D, w.cross(design3d.Y3D), w))
    sections.append(rounded_rectangle(width, height, 0.02))

beam = primitives3d.Loft(sections, frames, name="Tapered beam")

# An open surface interpolating open wires
wires3d = [
    wires.Wire3D.from_points(
        [
            design3d.Point3D(x, -0.2, 0.0),
            design3d.Point3D(x, 0.0, 0.1 + 0.05 * math.cos(10 * x)),
            design3d.Point3D(x, 0.2, 0.0),
        ]
    )
    for x in (0.6, 0.8, 1.0)
]
roof = shells.OpenShell3D(primitives3d.loft_faces(wires3d), name="Roof")

model = design3d.core.VolumeModel([beam, roof])
model.babylonjs()
model.to_step("loft.step")
