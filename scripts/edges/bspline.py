#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 16:23:49 2021

@author: steven
"""

import volmdlr as d3d
import volmdlr.edges as d3de

# 2D
points2d = [d3d.Point2D(0, 0),
            d3d.Point2D(0.1, 0.1),
            d3d.Point2D(0, 0.2)]

curve2d = d3de.BSplineCurve2D(degree=2,
                             control_points=points2d,
                             knot_multiplicities=[1, 2, 2, 1],
                             knots=[0.1, 0.3, 0.5, 0.7])
curve2d.plot()

# 3D
points3d = [d3d.Point3D(0, 0, 0),
            d3d.Point3D(0.1, 0.1, 0),
            d3d.Point3D(0, 0.2, 0.05)]

curve3d = d3de.BSplineCurve3D(degree=2,
                               control_points=points3d,
                               knot_multiplicities=[1, 2, 2, 1],
                               knots=[0.1, 0.3, 0.5, 0.7])
curve3d.plot()
