"""
Tests for faces 3D
"""
import unittest
import math
import design3d
from design3d import faces, surfaces


class TestFace3D(unittest.TestCase):
    def test_point_distance(self):
        radius = 0.15
        cylindricalsurface = surfaces.CylindricalSurface3D(design3d.OXYZ, radius)
        cylindricalface = faces.CylindricalFace3D.from_surface_rectangular_cut(cylindricalsurface, 0,
                                                                               design3d.TWO_PI / 3, -.25,
                                                                               .25)
        point3d = design3d.Point3D(.05, .05, -0.05)
        distance, point1 = cylindricalface.point_distance(point3d, True)
        self.assertAlmostEqual(distance, 0.07871852659452186, 4)
        self.assertTrue(point1.is_close(design3d.Point3D(radius / math.sqrt(2), radius / math.sqrt(2), -0.05), 1e-3))


if __name__ == '__main__':
    unittest.main()
