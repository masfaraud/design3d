#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 14 13:55:59 2017

@author: steven
"""

# Debug of area and inertia

import design3d as d3d

r=0.05

p1=d3d.Point2D(0,0)
p2=d3d.Point2D(0,-r)
p3=d3d.Point2D(r,0)
p4=d3d.Point2D(0,r)

c1=d3d.edges.Arc2D(p2,p3,p4)

print(c1.second_moment_area(p1))

c2=d3d.wires.Circle2D(p1,r)

print(c2.second_moment_area(p1))
