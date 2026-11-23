#!/usr/bin/env python3
"""
Created on Thu Mar 23 13:03:54 2023

@author: masfaraud
"""

import math

import design3d as d3d
from design3d import core as d3dc
from design3d import primitives2d as p2d
from design3d import primitives3d as p3d
from design3d import wires as d3dw

GAP = 8
SNAKE_WIDTH = 61
TAIL_OFFSET = 72
EYE_RADIUS = 12

radius = 0.7 * SNAKE_WIDTH

center = d3d.Point3D(0.0, -SNAKE_WIDTH - 0.5 * GAP, 0)
eye_center = d3d.Point2D(-36, 36)

p1 = d3d.Point2D(0.0, 0.0)
p2 = d3d.Point2D(0.0, GAP)
p3 = d3d.Point2D(-SNAKE_WIDTH, GAP)
p4 = d3d.Point2D(-SNAKE_WIDTH, GAP + SNAKE_WIDTH)
p5 = d3d.Point2D(SNAKE_WIDTH, GAP + SNAKE_WIDTH)
p6 = d3d.Point2D(SNAKE_WIDTH, -SNAKE_WIDTH)
p7 = d3d.Point2D(-TAIL_OFFSET, -SNAKE_WIDTH)
p8 = d3d.Point2D(-TAIL_OFFSET, -SNAKE_WIDTH - TAIL_OFFSET)
p9 = d3d.Point2D(-TAIL_OFFSET - SNAKE_WIDTH, -SNAKE_WIDTH - TAIL_OFFSET)
p10 = d3d.Point2D(-TAIL_OFFSET - SNAKE_WIDTH, 0.0)

snake1_eye = d3dw.Contour2D.from_circle(d3d.curves.Circle2D(d3d.Frame2D(eye_center, d3d.X2D, d3d.Y2D), EYE_RADIUS))

snake1_contour = p2d.ClosedRoundedLineSegments2D(
    [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10], {3: radius, 4: radius, 5: radius, 6: radius, 8: radius, 9: radius}
)

snake1_contour.plot()

snake1 = p3d.ExtrudedProfile(
    d3d.OXYZ,
    snake1_contour,
    [snake1_eye],
    GAP,
    color=(0.188, 0.412, 0.596),
    name="Blue snake",
)
snake2 = snake1.rotation(center, d3d.Z3D, math.pi)
snake2.color = (1, 0.867, 0.329)
snake2.name = "Yellow snake"

model = d3dc.VolumeModel([snake1, snake2])
model.babylonjs()
