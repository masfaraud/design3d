#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A sweep using a bspline.
"""
import math

import matplotlib.pyplot as plt

import design3d as d3d
import design3d.edges as d3de
import design3d.wires as d3dw
from design3d import primitives3d, curves
from design3d.core import EdgeStyle

degree = 5
control_points = [d3d.Point3D(0, 0, 0),
                  d3d.Point3D(0.3, 0.2, 0.1),
                  d3d.Point3D(0.5, -0.1, 0.4),
                  d3d.Point3D(0.5, -0.4, 0.0),
                  d3d.Point3D(-0.1, -0.2, -0.3),
                  d3d.Point3D(-0.3, 0.4, 0.1)]
knots = [0.0, 1.0]
knot_multiplicities = [6, 6]
weights = None  # [1, 2, 1, 2, 1, 2]
bspline_curve3d = d3de.BSplineCurve3D(degree=degree,
                                     control_points=control_points,
                                     knot_multiplicities=knot_multiplicities,
                                     knots=knots,
                                     weights=weights,
                                     name='B Spline Curve 3D 1')

circle = curves.Circle2D(d3d.OXY, 0.015)
contour = d3dw.Contour2D(circle.split_at_abscissa(circle.length()*.5))

# rl = primitives3d.OpenRoundedLineSegments3D(points, radius, adapt_radius=True, name='wire')


sweep = primitives3d.Sweep(contour, d3dw.Wire3D([bspline_curve3d]), name='Random pipe')

model = d3d.core.VolumeModel([sweep])
model.babylonjs()

model.to_step('bspline_sweep.step')
