#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar 14 15:32:37 2018

@author: Steven Masfaraud masfaraud@dessia.tech
"""
#import volmdlr.primitives2D as primitives2D
import numpy as npy

import volmdlr as d3d
import volmdlr.edges as d3de
import volmdlr.wires as d3dw

#for i in range(20):
triangle_points=[d3d.Point2D.random(0, 1, 0, 1) for i in range(3)]
triangle = d3dw.ClosedPolygon2D(triangle_points)


# cog_triangle = triangle.center_of_mass()
# c1 = d3d.core.CompositePrimitive2D([triangle, cog_triangle])
# c1.plot()

print(triangle.area())

p0=d3d.Point2D(-1,0)
p1=d3d.Point2D(-npy.cos(npy.pi/4),npy.sin(npy.pi/4))
p2=d3d.Point2D(0,1)

a = d3de.Arc2D.from_3_points(p2,p1,p0)
l = d3de.LineSegment2D(p2, a.circle.center)
#list_node = a.Discretise()

c = d3dw.Contour2D([a, l])
print(c.plot_data())
print(c.area())
