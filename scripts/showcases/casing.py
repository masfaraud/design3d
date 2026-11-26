#!/usr/bin/env python3
"""
Test case representing a stamped casing. Use extrusion features.

The walls flare with a draft angle, as a stamped sheet: the outer contour and the hole flare together, so that the
walls keep their thickness. The belt lies on the flared walls.
"""

import math

import design3d as d3d
import design3d.wires
from design3d import curves, edges, primitives2d, primitives3d

THICKNESS = 0.005
HEIGHT = 0.080
DRAFT_ANGLE = math.radians(5)
SCREW_HOLES_DIAMETER = 0.006
SCREW_HOLES_CLEARANCE = 0.003
N_SCREWS = 25

p1 = d3d.Point2D(0, 0)
p2 = d3d.Point2D(0.3, 0)
p3 = d3d.Point2D(0.33, 0.22)
p4 = d3d.Point2D(0.2, 0.08)
p5 = d3d.Point2D(0.16, 0.18)
p6 = d3d.Point2D(0.05, 0.20)

inner_contour = primitives2d.ClosedRoundedLineSegments2D(
    [p1, p2, p3, p4, p5, p6], {0: 0.01, 1: 0.01, 2: 0.015, 3: 0.020, 4: 0.012, 5: 0.008}, adapt_radius=True
)

outer_contour = inner_contour.offset(THICKNESS)

# The outer contour flares (negative draft) and the hole widens (positive draft) by the same amount.
sides = primitives3d.ExtrudedProfile(
    d3d.OXYZ,
    outer_contour,
    [inner_contour],
    HEIGHT - 2 * THICKNESS,
    draft_angle=-DRAFT_ANGLE,
    inner_draft_angles=[DRAFT_ANGLE],
    name="sides",
)

bottom = primitives3d.ExtrudedProfile(d3d.OXYZ, outer_contour, [], -THICKNESS, name="bottom")

# The inner contour at the top of the flared walls, on which the belt lies.
top_inner_contour = inner_contour.offset((HEIGHT - 2 * THICKNESS) * math.tan(DRAFT_ANGLE))

screw_holes_rl = top_inner_contour.offset(THICKNESS + SCREW_HOLES_CLEARANCE + 0.5 * SCREW_HOLES_DIAMETER)
screw_holes = []
length = screw_holes_rl.length()
for i in range(N_SCREWS):
    s = i * length / N_SCREWS
    p = screw_holes_rl.point_at_abscissa(s)
    circle = curves.Circle2D(design3d.Frame2D(p, design3d.X2D, design3d.Y2D), SCREW_HOLES_DIAMETER * 0.5)
    screw_holes.append(design3d.wires.Contour2D([edges.FullArc2D.from_curve(circle)]))

belt_outer_contour = top_inner_contour.offset(2 * SCREW_HOLES_CLEARANCE + SCREW_HOLES_DIAMETER + THICKNESS)
belt = primitives3d.ExtrudedProfile(
    design3d.Frame3D(d3d.Point3D(0, 0, 1) * (HEIGHT - 2 * THICKNESS), d3d.X3D, d3d.Y3D, d3d.Z3D),
    belt_outer_contour,
    [top_inner_contour] + screw_holes,
    THICKNESS,
    name="belt",
)

casing = d3d.core.VolumeModel([bottom, sides, belt], name="Casing")
