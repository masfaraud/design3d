import unittest
from math import pi

import design3d
from design3d.primitives3d import Sphere


class TestSphere(unittest.TestCase):
    def setUp(self):
        self.sphere = Sphere(
            center=design3d.O3D,
            radius=0.02,
        )

    def test_point_belongs(self):
        self.assertTrue(self.sphere.point_belongs(design3d.O3D))
        self.assertFalse(self.sphere.point_belongs(design3d.Point3D(1, 0, 0)))

    def test_volume(self):
        volume = 4 / 3 * pi * self.sphere.radius**3
        self.assertEqual(self.sphere.volume(), volume)


if __name__ == "__main__":
    unittest.main()
