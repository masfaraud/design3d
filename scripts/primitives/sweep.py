#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A sweep example.
"""

import random
import matplotlib.pyplot as plt
import design3d

import design3d as d3d
import design3d.primitives3d as primitives3d
import design3d.wires as wires
from design3d import curves

random.seed(2)

p1 = design3d.Point3D(0, 0, 0)
p2 = design3d.Point3D(-0.150, 0, 0)
p3 = design3d.Point3D(-0.150, 0.215, 0)
p4 = design3d.Point3D(-0.150, 0.215, -0.058)
p5 = design3d.Point3D(-0.220, 0.186, -0.042)

points = [p1, p2, p3, p4, p5]
radius = {1: 0.015, 2: 0.020, 3: 0.03}

current_point = p5

for i in range(6):
    current_point += design3d.Point3D.random(-0.1, 0.3, -0.1, 0.3, -0.1, 0.3)
    points.append(current_point)
    radius[4 + i] = 0.01 + 0.03 * random.random()


open_rounded_line_segements = primitives3d.OpenRoundedLineSegments3D(points, radius, adapt_radius=True, name='wire')


# contour = wires.Circle2D(d3d.O2D, 0.008)
contour = wires.ClosedPolygon2D([design3d.Point2D(-0.004, -0.004), design3d.Point2D(0.004, -0.004),
                                 design3d.Point2D(0.004, 0.004), design3d.Point2D(-0.004, 0.004)])

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
# r1 = open_rounded_line_segements.to_dict()
# r2 = primitives3d.OpenRoundedLineSegments3D.dict_to_object(r1)
# c1 = contour.to_dict()
# c2 = curves.Circle2D.dict_to_object(c1)
origin = open_rounded_line_segements.primitives[0].start
w = open_rounded_line_segements.primitives[0].unit_direction_vector(0.)
u = open_rounded_line_segements.primitives[0].unit_normal_vector(0.)
if not u:
    u = w.deterministic_unit_normal_vector()
v = w.cross(u)
frame = design3d.Frame3D(origin, u, v, w)
frame.plot(ax, ratio=0.01)
open_rounded_line_segements.primitives[0].start.plot(ax)
for prim in open_rounded_line_segements.primitives:
    prim.plot(ax=ax)
    frame = prim.move_frame_along(frame)
    frame.plot(ax, ratio=0.025)



sweep = primitives3d.Sweep(contour, open_rounded_line_segements, name='Random pipe')

model = d3d.core.VolumeModel([sweep])
model.babylonjs()

model.to_step('sweep.step')

contour = wires.ClosedPolygon2D([design3d.Point2D(-0.008, -0.004), design3d.Point2D(0.008, -0.004),
                                 design3d.Point2D(0.008, 0.004), design3d.Point2D(-0.008, 0.004)])

sweep = primitives3d.Sweep(contour, open_rounded_line_segements, name='Random pipe')
model = d3d.core.VolumeModel([sweep])
model.babylonjs()

model.to_step('sweep.step')
