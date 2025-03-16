#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Surface2D examples
"""

import design3d
import design3d.primitives2d as p2d
from design3d import wires, surfaces, curves
l = 0.12
e1 = 0.015
e2 = 0.015
h1 = 0.035
h2 = 0.052
h3 = 0.018
r = 0.5*e2


p1 = design3d.Point2D(0, 0)
p2 = design3d.Point2D(l, 0)
p3 = design3d.Point2D(l, h1)
p4 = design3d.Point2D(e1, h1)
p5 = design3d.Point2D(0., h2+h3)
p6 = design3d.Point2D(-2.5*e2, h2+h3)

pc = design3d.Point2D(-e2, h2)

contour = design3d.primitives2d.ClosedRoundedLineSegments2D([p1, p2,
                                                            p3, p4,
                                                            p5, p6],
                                                            {0: r,
                                                             1: r,
                                                             4: r,
                                                             5: r},
                                                           adapt_radius=True)

# contour.plot()
hole = curves.Circle2D(design3d.OXY.translation(pc), 0.5*r)
surface = surfaces.Surface2D(contour, [hole])
surface.plot()

surface._check_platform()
