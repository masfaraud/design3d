#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Mar  8 10:58:19 2017

@author: steven
"""

import design3d as d3d
from design3d import curves

p1 = d3d.Point2D(1,1.45)
p2 = d3d.Point2D(0.4,0.1)
l1 = curves.Line2D(p1, p2)

p3 = d3d.Point2D(-1,0)
p4 = d3d.Point2D(1,-0.5)
l2 = curves.Line2D(p3, p4)

p5,bl1,bl2 = d3d.Point2D.line_intersection(l1, l2,True)
p6 = d3d.Point2D.middle_point(p1,p3)

p7 = d3d.Point2D.line_projection(p6, l1)
p8 = d3d.Point2D.line_projection(p6, l2)

ax = l1.plot()
for p in [l2, p5, p6, p7 ,p8]:
    p.plot(ax=ax)
