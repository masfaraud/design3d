#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun  7 16:23:04 2021

@author: masfaraud
"""

import design3d as d3d
import design3d.core as d3dc
import design3d.wires as d3dw

p1 = d3d.Point2D(0, 0)
p2 = d3d.Point2D(27.768772992234517, 0.0)
p3 = d3d.Point2D(29.285641835268507, 0.605864117805322)

# Point2D: [0.0, 0.0], Point2D: [], Point2D: []]

tri = d3dw.ClosedPolygon2D([p1, p2, p3])
m = tri.triangulation()
m.plot()
