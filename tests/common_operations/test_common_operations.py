import unittest

import design3d
from design3d.surfaces import Plane3D
from design3d.utils.common_operations import split_wire_by_plane
from design3d import primitives3d
import random


random.seed(2)

p1 = design3d.Point3D(0, 0, 0)
p2 = design3d.Point3D(-0.150, 0, 0)
p3 = design3d.Point3D(-0.150, 0.215, 0)
p4 = design3d.Point3D(-0.150, 0.215, -0.058)
p5 = design3d.Point3D(-0.220, 0.186, -0.042)

points = [p1, p2, p3, p4, p5]
radius = {1: 0.015, 2: 0.020, 3: 0.03}

current_point = p5

for i in range(6):
    current_point += design3d.Point3D.random(-0.1, 0.3, -0.1, 0.3, -0.1, 0.3)
    points.append(current_point)
    radius[4 + i] = 0.01 + 0.03 * random.random()


open_rounded_line_segements = primitives3d.OpenRoundedLineSegments3D(points, radius, adapt_radius=True, name='wire')

class TestCommonOperations(unittest.TestCase):
    def test_split_wire_by_plane(self):
        plane = Plane3D.from_plane_vectors(design3d.Point3D(0.4, 0.4, 0.2), design3d.Vector3D(1, 0, 0),
                                           design3d.Vector3D(0, 1, 0))
        wire1, wire2 = split_wire_by_plane(open_rounded_line_segements, plane)
        self.assertEqual(wire1.length(), 1.4187473149621863)
        self.assertAlmostEqual(wire2.length(), 0.6182864075957109)


if __name__ == "__main__":
    unittest.main()
