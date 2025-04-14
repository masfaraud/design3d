#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 22:36:57 2025

@author: steven
"""

from geomdl import utilities
import design3d
from design3d import edges, curves

DEGREE = 3
points = [design3d.Point2D(0, 0), design3d.Point2D(1, 1), design3d.Point2D(2, -1), design3d.Point2D(3, 0)]
knotvector = utilities.generate_knot_vector(DEGREE, len(points))
knot_multiplicity = [1] * len(knotvector)
bspline1 = edges.BSplineCurve2D(DEGREE, points, knot_multiplicity, knotvector, None)

lineseg = edges.LineSegment2D(design3d.Point2D(0, 0.2), design3d.Point2D(3, -0.2))

arc = edges.Arc2D.from_3_points(design3d.Point2D(0, 0.3), design3d.Point2D(1, -0.3), design3d.Point2D(2, 2))
u_vector = design3d.Vector2D(0.7071067811865475, 0.7071067811865475)
v_vector = design3d.Vector2D(-0.7071067811865475, 0.7071067811865475)
frame = design3d.Frame2D(design3d.O2D, u_vector, v_vector)
ellipse2d = curves.Ellipse2D(2, 1, frame)
arc_ellipse2d = edges.ArcEllipse2D(ellipse2d, start=design3d.Point2D(0.5, 1.5), end=design3d.Point2D(1.5, 0.5))


def bspline_curve3d():
    """Bspline curve3d model."""
    degree = 5
    control_points = [design3d.Point3D(0, 3, 0),
                      design3d.Point3D(3, 2, 1),
                      design3d.Point3D(5, -1, 4),
                      design3d.Point3D(5, -4, 0),
                      design3d.Point3D(-1, -2, -3),
                      design3d.Point3D(-3, 4, 1)]
    knots = [0.0, 1.0]
    knot_multiplicities = [6, 6]
    weights = None  # [1, 2, 1, 2, 1, 2]
    return edges.BSplineCurve3D(degree=degree, control_points=control_points,
                                knot_multiplicities=knot_multiplicities,
                                knots=knots,
                                weights=weights,
                                name='B Spline Curve 3D 1')


vector1 = design3d.Vector3D(1, 1, 1)
vector1 = vector1.unit_vector()
vector2 = vector1.deterministic_unit_normal_vector()
vector3 = vector1.cross(vector2)


def arc3d():
    """Arc 3d model."""
    circle3d = curves.Circle3D(design3d.Frame3D(design3d.O3D, vector1, vector2, vector3), 1)
    return edges.Arc3D(circle3d, start=design3d.Point3D(0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
                       end=design3d.Point3D(-0.9855985596534886, -0.11957315586905026, -0.11957315586905026))


def arc_ellipse3d():
    """Arc ellipse 3d model."""
    ellipse3d = curves.Ellipse3D(2, 1, design3d.Frame3D(design3d.Point3D(1, 2, 1), vector3, vector1, vector2))
    return edges.ArcEllipse3D(ellipse3d,
                              start=design3d.Point3D(0.42264973081037405, 1.4226497308103743, 0.42264973081037427),
                              end=design3d.Point3D(1.577350269189626, 2.5773502691896253, 1.5773502691896257))


def linesegment3d():
    """Linesegment 3d model."""
    return edges.LineSegment3D(design3d.Point3D(1, 2, 4), design3d.Point3D(-1, 5, -3))
