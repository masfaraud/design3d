"""
Test script for cylinder discretization
"""

import design3d as d3d
from design3d.primitives3d import Cylinder

c = Cylinder.from_center_point_and_axis(
    center_point=d3d.Point3D(0, 0.1, 0),
    axis=d3d.Vector3D(1, 0, 0),
    radius=0.01,
    length=0.1,
    color=(1, 0, 0),
)

n_points = 1000

ay = c.random_point_inside().plot()
for _ in range(n_points):
    c.random_point_inside().plot(ax=ay)

points = c.lhs_points_inside(n_points)
ax = points[0].plot()
for p in points:
    p.plot(ax=ax)
