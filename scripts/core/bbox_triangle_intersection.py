"""
Showcase of BoundingBox / Triangle3D intersection
"""
from design3d.core import BoundingBox
from design3d.faces import Triangle3D
import design3d

bounding_box = BoundingBox(0.0, 2.0, 0.0, 2.0, 0.0, 2.0)

p0 = design3d.Point3D(5, -3, 0.5)
p1 = design3d.Point3D(-3, 5, 0.5)
p2 = design3d.Point3D(5, 5, 0.5)
triangle = Triangle3D(p0, p1, p2)

ax = bounding_box.plot()
triangle.plot(ax=ax)

print(bounding_box.is_intersecting_triangle(triangle))
