"""
design3d init module.
"""
# -*- coding: utf-8 -*-
import math

import pkg_resources

__version__ = pkg_resources.require("design3d")[0].version

from design3d.core_compiled import (O2D, O3D, OXY, X2D, X3D, Y2D, Y3D, Z3D,
                                   Basis2D, Basis3D, Frame2D, Frame3D,
                                   linesegment2d_point_distance, LineSegment3DDistance,
                                   linesegment3d_point_distance, get_minimum_distance_points_lines,
                                   Matrix22, Matrix33, Point2D, Point3D, Vector2D,
                                   Vector3D)


TWO_PI = 2 * math.pi

XYZ = Basis3D(X3D, Y3D, Z3D)
YZX = Basis3D(Y3D, Z3D, X3D)
ZXY = Basis3D(Z3D, X3D, Y3D)

OXYZ = Frame3D(O3D, X3D, Y3D, Z3D)
OYZX = Frame3D(O3D, Y3D, Z3D, X3D)
OZXY = Frame3D(O3D, Z3D, X3D, Y3D)

PATH_ROOT = "#"
