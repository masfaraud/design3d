#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov  6 10:25:22 2019

@author: ringhausen
"""

import math

import design3d as d3d
import design3d.edges as d3de
import design3d.primitives2d as p2d
import design3d.primitives3d as p3d
import design3d.wires as d3dw

# %%

p1 = d3d.Point2D(0, 0)
p2 = d3d.Point2D(0, 2)
p3 = d3d.Point2D(2, 4)
p4 = d3d.Point2D(4, 4)
p5 = d3d.Point2D(4, 3)
p6 = d3d.Point2D(3, 2)
p7 = d3d.Point2D(3, 0)

l1 = p2d.OpenedRoundedLineSegments2D([p7, p1, p2], {})
l2 = d3de.Arc2D.from_3_points(p2, d3d.Point2D(math.sqrt(2) / 2, 3 + math.sqrt(2) / 2), p3)
l3 = p2d.OpenedRoundedLineSegments2D([p3, p4, p5, p6], {}, adapt_radius=True)
l4 = d3de.Arc2D.from_3_points(p6, d3d.Point2D(4, 1), p7)
c1 = d3dw.Contour2D([l1, l2, l3, l4])

p8 = d3d.Point2D(1, 1)
p9 = d3d.Point2D(2, 1)
p10 = d3d.Point2D(2, 2)
p11 = d3d.Point2D(1, 2)
c2 = p2d.ClosedRoundedLineSegments2D([p8, p9, p10, p11], {})
# c2 = d3dw.Contour2D([inner])

profile = p3d.ExtrudedProfile(d3d.OXYZ, c1, [], 1)
# profile.plot()

model = d3d.core.VolumeModel([profile])
model.babylonjs()

# %%

p1 = d3d.Point2D(0, 0)
p2 = d3d.Point2D(2, 0)
p3 = d3d.Point2D(2, 2)
p4 = d3d.Point2D(0, 2)

p5 = d3d.Point2D(0.5, 0.5)
p6 = d3d.Point2D(1.5, 0.5)
p7 = d3d.Point2D(1.5, 1.5)
p8 = d3d.Point2D(0.5, 1.5)

l1 = p2d.ClosedRoundedLineSegments2D([p1, p2, p3, p4], {})
c1 = d3d.wires.Contour2D(l1.primitives)

l2 = p2d.ClosedRoundedLineSegments2D([p5, p6, p7, p8], {})
c2 = d3d.wires.Contour2D(l2.primitives)

profile = p3d.ExtrudedProfile(d3d.OXYZ, c1, [c2], 1)

model = d3d.core.VolumeModel([profile])
model.babylonjs()
