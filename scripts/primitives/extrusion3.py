#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""

import math

import design3d as d3d
import design3d.core as d3dc
import design3d.edges
import design3d.edges as d3de
import design3d.wires as d3dw
from design3d.primitives3d import ExtrudedProfile
from design3d import curves
number_holes = 5

outer_circle = d3dw.Contour2D([design3d.edges.FullArc2D.from_curve(curves.Circle2D(d3d.OXY, 0.06))])


delta_angle = 2*math.pi/number_holes
inner_circle = d3dw.Contour2D([design3d.edges.FullArc2D.from_curve(curves.Circle2D(d3d.OXY, 0.04))])
first_circle = d3dw.Contour2D([design3d.edges.FullArc2D.from_curve(curves.Circle2D(
    d3d.OXY.translation(d3d.Vector2D(0, 0.05)), 0.005))])
circles = [inner_circle, first_circle]

extrusion_length = 0.1

for i in range(1, number_holes):
    circles.append(first_circle.rotation(d3d.O2D, i*delta_angle))


extrusion = ExtrudedProfile(d3d.OYZX, outer_circle, circles, extrusion_length)

inner_circles_area = sum([c.area() for c in circles])
assert math.isclose(extrusion.volume(), (outer_circle.area() - inner_circles_area)*extrusion_length)

model = d3dc.VolumeModel([extrusion])
model.babylonjs()
model._check_platform()
