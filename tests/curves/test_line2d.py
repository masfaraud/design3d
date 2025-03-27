import unittest

import design3d
from design3d import curves


class TestLine2D(unittest.TestCase):

    def test_point_distance(self):
        line_2d = curves.Line2D(design3d.Point2D(0, 0), design3d.Point2D(1, 1))
        self.assertEqual(line_2d.point_distance(design3d.Point2D(2, 2)), 0.0)
        self.assertEqual(line_2d.point_distance(design3d.Point2D(1, 2)), 0.7071067811865475)

    def test_point_belongs(self):
        line = curves.Line2D(design3d.O2D, design3d.Point2D(1, 1))
        point1 = design3d.Point2D(2, 2)
        point2 = design3d.Point2D(1, 2)
        self.assertTrue(line.point_belongs(point1))
        self.assertFalse(line.point_belongs(point2))

    def test_sort_points_along_line(self):
        line2d = curves.Line2D(design3d.O2D, design3d.Point2D(1, 2))
        list_points2d = [design3d.Point2D(2, 4), design3d.Point2D(1.5, 3),
                         design3d.Point2D(4, 8), design3d.Point2D(2.5, 5)]
        sorted_points_along_line2d = line2d.sort_points_along_curve(list_points2d)
        expected_sorted_points2d = [design3d.Point2D(1.5, 3), design3d.Point2D(2, 4),
                                    design3d.Point2D(2.5, 5), design3d.Point2D(4, 8)]
        for point, expected_point in zip(sorted_points_along_line2d, expected_sorted_points2d):
            self.assertEqual(point, expected_point)


if __name__ == '__main__':
    unittest.main()
