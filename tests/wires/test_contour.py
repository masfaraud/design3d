"""
Unit tests for design3d.wires.Contour
"""
import unittest

import design3d.wires


class TestContour(unittest.TestCase):

    def test_is_overlapping(self):
        p1 = [design3d.Point2D(-0.2, -0.2), design3d.Point2D(0.2, -0.2),
              design3d.Point2D(0.2, 0.2), design3d.Point2D(-0.2, 0.2)]

        contour1 = design3d.wires.ClosedPolygon2D(p1)
        contour2 = contour1.translation(design3d.Vector2D(0.5,0))
        contour3 = contour1.translation(design3d.Vector2D(0.1,0))
        
        self.assertFalse(contour1.is_overlapping(contour2))
        self.assertTrue(contour1.is_overlapping(contour3))


if __name__ == '__main__':
    unittest.main()
