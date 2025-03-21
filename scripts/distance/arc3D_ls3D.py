# -*- coding: utf-8 -*-
"""
Created on Fri May 22 11:17:00 2020

@author: Mack Pro
"""


import random

import matplotlib.pyplot as plt

import volmdlr as d3d
import volmdlr.edges as d3de
from volmdlr.utils.common_operations import minimum_distance_points_circle3d_linesegment3d
### Cas arc/LS

mini, maxi = -5, 5

pt1 = d3d.Point3D.random(mini, maxi, mini, maxi, mini, maxi)
pt2 = d3d.Point3D.random(mini, maxi, mini, maxi, mini, maxi)
ptmid = ( pt1 + pt2 )/2
pt_midmid = pt1 + (pt2-pt1)/4
pt_midmid2 = pt2 + (pt1-pt2)/4
LS1 = d3de.LineSegment3D(pt1, pt2)

pt = d3d.Point3D.random(mini, maxi, mini, maxi, mini, maxi)
radius = 2
start, interior, end = pt, pt + d3d.Point3D(0,-radius,radius),pt + d3d.Point3D(0,-radius,-radius)
arc = d3de.Arc3D.from_3_points(start, interior, end)

fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
pt1.plot(ax=ax)
pt2.plot(ax=ax, color='r')
LS1.plot(ax=ax)
start.plot(ax=ax,color='g')
interior.plot(ax=ax,color='b')
end.plot(ax=ax,color='y')
arc.plot(ax=ax)
ptmid.plot(ax=ax)

pta1, pta2 = minimum_distance_points_circle3d_linesegment3d(arc, LS1)
pta1.plot(ax=ax, color='m')
pta2.plot(ax=ax, color='m')

print('int',(interior-pt2).norm(), (interior-pt1).norm())
print('start',(start-pt2).norm(), (start-pt1).norm())
print('end',(end-pt2).norm(), (end-pt1).norm())

d_min = LS1.minimum_distance(arc)
print('d_min',d_min)
