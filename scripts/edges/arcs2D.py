#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Oct 23 18:06:45 2018

@author: steven
"""

import design3d
import design3d.edges

# Random arc
i = design3d.Point2D.random(-1,1,-1,1)
e = design3d.Point2D.random(-1,1,-1,1)
s = design3d.Point2D.random(-1,1,-1,1)


a = design3d.edges.Arc2D.from_3_points(s, i, e)
ax = a.plot()

for p in a.discretization_points(number_points=10):
    p.plot(ax=ax)

s.plot(ax=ax, color='r')
e.plot(ax=ax, color='g')
i.plot(ax=ax, color='b')
