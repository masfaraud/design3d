import math
import unittest

import design3d
from design3d.primitives3d import Cylinder


class TestCylinder(unittest.TestCase):
    def setUp(self) -> None:
        self.cylinder1 = Cylinder(
            frame=design3d.Frame3D.from_point_and_normal(design3d.Point3D(0, 0, 0), design3d.Vector3D(1, 0, 0)),
            radius=0.02,
            length=0.1,
            color=(0, 0, 1),
        )

        self.cylinder2 = Cylinder(
            frame=design3d.Frame3D.from_point_and_normal(design3d.Point3D(0.05, 0, 0), design3d.Vector3D(0, 1, 0)),
            radius=0.005,
            length=0.01,
            color=(1, 0, 1),
        )

        self.cylinder3 = Cylinder(
            frame=design3d.Frame3D.from_point_and_normal(design3d.Point3D(0.15, 0, 0), design3d.Vector3D(0, 1, 0)),
            radius=0.005,
            length=0.01,
            color=(1, 0, 1),
        )

    def test_point_belongs(self):
        self.assertTrue(self.cylinder1.point_belongs(design3d.O3D))
        self.assertFalse(self.cylinder1.point_belongs(design3d.Point3D(1, 0, 0)))

    def test_random_point_inside(self):
        point = self.cylinder1.random_point_inside()
        self.assertIsInstance(point, design3d.Point3D)
        self.assertTrue(self.cylinder1.point_belongs(point))

    def test_interference_volume_with_other_cylinder(self):
        interference_volume = self.cylinder1.interference_volume_with_other_cylinder(other_cylinder=self.cylinder1)
        self.assertEqual(interference_volume, self.cylinder1.volume())

    def test_min_distance_to_other_cylinder(self):
        dist_1_2 = self.cylinder1.min_distance_to_other_cylinder(self.cylinder2)
        dist_1_3 = self.cylinder1.min_distance_to_other_cylinder(self.cylinder3)

        self.assertAlmostEqual(dist_1_2, 0.0, delta=1e-5)
        self.assertAlmostEqual(dist_1_3, 0.095, delta=1e-5)

    def test_is_intersecting_other_cylinder(self):
        intersecting_1_2 = self.cylinder1.is_intersecting_other_cylinder(self.cylinder2)
        intersecting_1_3 = self.cylinder1.is_intersecting_other_cylinder(self.cylinder3)

        self.assertTrue(intersecting_1_2)
        self.assertFalse(intersecting_1_3)

    def test_lhs_points_inside(self):
        points = self.cylinder1.lhs_points_inside(n_points=100)
        for point in points:
            self.assertTrue(self.cylinder1.point_belongs(point))

    def test_from_end_points(self):
        point1 = design3d.Point3D(-1, 0, 0)
        point2 = design3d.Point3D(1, 0, 0)

        cylinder = Cylinder.from_end_points(point1, point2, 0.1)

        self.assertEqual(cylinder.position, design3d.O3D)
        self.assertEqual(cylinder.axis, design3d.X3D)
        self.assertEqual(cylinder.length, 2.0)
        self.assertEqual(cylinder.radius, 0.1)

    def test_from_center_point_and_axis(self):
        cylinder = Cylinder.from_center_point_and_axis(design3d.O3D, design3d.Z3D, 0.1, 1.0)

        self.assertEqual(cylinder.position, design3d.O3D)
        self.assertEqual(cylinder.axis, design3d.Z3D)
        self.assertEqual(cylinder.length, 1.0)
        self.assertEqual(cylinder.radius, 0.1)

    def test_rotation(self):
        rotated_cylinder = self.cylinder1.rotation(center=design3d.O3D, axis=design3d.Z3D, angle=math.pi / 2)
        self.assertTrue(rotated_cylinder.axis.is_close(design3d.Y3D))

    def test_translation(self):
        translated_cylinder = self.cylinder1.translation(offset=design3d.X3D)
        self.assertTrue(translated_cylinder.position.is_close(design3d.Point3D(1.0, 0.0, 0.0)))


if __name__ == "__main__":
    unittest.main()
