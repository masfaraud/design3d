"""
Unit tests for design3d.faces.BSplineCurve
"""
import unittest
import design3d
import design3d.edges as d3de


class TestBezierCurve2D(unittest.TestCase):
    # Set up the Bézier curve
    degree = 2
    ctrlpts = [design3d.Point2D(10, 0), design3d.Point2D(20, 15), design3d.Point2D(30, 0)]

    curve1 = d3de.BezierCurve2D(degree, ctrlpts)

    # Set evaluation delta
    curve1.sample_size = 5

    def test_setup(self):
        points = self.curve1.points
        expected_points = [[10.0, 0.0], [15.0, 5.625], [20.0, 7.5], [25.0, 5.625], [30.0, 0.0]]
        expected_knot_vector = [0.0, 0.0, 0.0, 1.0, 1.0, 1.0]

        self.assertEqual(self.curve1.knotvector.tolist(), expected_knot_vector)
        for point, test in zip(points, expected_points):
            self.assertAlmostEqual(point[0], test[0], delta=1e-6)
            self.assertAlmostEqual(point[1], test[1], delta=1e-6)


if __name__ == '__main__':
    unittest.main()
