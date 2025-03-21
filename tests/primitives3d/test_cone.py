import math
import unittest

import design3d
from design3d.primitives3d import Cone


class TestCone(unittest.TestCase):
    def setUp(self) -> None:
        self.radius = 0.1
        self.length = 0.1
        self.cone = Cone(frame=design3d.OXYZ, radius=self.radius, length=self.length)

    def test_point_belongs(self):
        self.assertTrue(self.cone.point_inside(design3d.O3D))
        self.assertTrue(self.cone.point_inside(design3d.Point3D(0.0, 0.0, self.length / 2)))
        self.assertTrue(self.cone.point_inside(design3d.Point3D(-self.radius, 0.0, -self.length / 2)))
        self.assertTrue(self.cone.point_inside(design3d.Point3D(0.0, -self.radius, -self.length / 2)))
        self.assertFalse(self.cone.point_inside(design3d.Point3D(0.0, 0.0, self.length)))
        self.assertFalse(self.cone.point_inside(design3d.Point3D(0.01, 0.01, self.length / 2)))

    def test_volume(self):
        self.assertEqual(self.cone.volume(), (math.pi * 0.1 * self.radius**2) / 3)

    def test_from_center_point_and_axis(self):
        cone = Cone.from_center_point_and_axis(design3d.O3D, design3d.Z3D, 0.1, 1.0)

        self.assertEqual(cone.position, design3d.O3D)
        self.assertEqual(cone.axis, design3d.Z3D)
        self.assertEqual(cone.length, 1.0)
        self.assertEqual(cone.radius, 0.1)

    def test_rotation(self):
        rotated_cone = self.cone.rotation(center=design3d.O3D, axis=design3d.X3D, angle=-math.pi / 2)
        self.assertTrue(rotated_cone.axis.is_close(design3d.Y3D))

    def test_translation(self):
        translated_cone = self.cone.translation(offset=design3d.X3D)
        self.assertTrue(translated_cone.position.is_close(design3d.Point3D(1.0, 0.0, 0.0)))
