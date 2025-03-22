import unittest

import design3d

from design3d import surfaces, wires


class TestSurface2D(unittest.TestCase):
    contour = wires.Contour2D.from_points([design3d.O2D, design3d.Point2D(1, 0), design3d.Point2D(1, 1),
                                           design3d.Point2D(0, 1)])
    surface2d = surfaces.Surface2D(contour, [])

    def test_triangulation(self):
        tri = self.surface2d.triangulation()
        tri.plot()
        self.assertAlmostEqual(self.surface2d.triangulation().area(), 1)


if __name__ == '__main__':
    unittest.main()
