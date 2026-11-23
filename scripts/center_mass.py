#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 19:23:27 2019

@author: steven
"""

import math


import design3d as d3d
import design3d.edges as edges
import design3d.wires as wires

r = 0.23

p1 = d3d.Point2D(0, 0)
p2 = d3d.Point2D(r, r)
p3 = d3d.Point2D(2 * r, 0)

a = edges.Arc2D.from_3_points(p1, p2, p3)
l = edges.LineSegment2D(p3, p1)

c = wires.Contour2D([a, l])
ax = c.plot()
cog = c.center_of_mass()
cog.plot(ax)


assert math.isclose(a.radius, r)
assert math.isclose(c.area(), math.pi * r**2 / 2.0)
assert math.isclose(cog[0], r)
print(cog[1], 4 * r / 3.0 * math.pi)
assert math.isclose(cog[1], 4 * r / 3.0 / math.pi)
