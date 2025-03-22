"""
Unit tests for design3d.faces.BSplineCurve
"""
import unittest
import design3d
import design3d.edges as d3de


class TestBezierCurve3D(unittest.TestCase):
    # Set up the Bézier curve
    degree = 3
    ctrlpts = [design3d.Point3D(0, 0, 0),
              design3d.Point3D(1, 1, 2),
              design3d.Point3D(2, 1, 1),
              design3d.Point3D(3, 0, 4)]
    bezier_curve3d = d3de.BezierCurve3D(degree=degree,
                                       control_points=ctrlpts,
                                       name='bezier curve 1')

    def test_cut_before(self):
        new_bezier = self.bezier_curve3d.cut_before(0.5)
        self.assertTrue(new_bezier.start.is_close(self.bezier_curve3d.evaluate_single(0.5)))
        self.assertTrue(new_bezier.end.is_close(self.bezier_curve3d.end))


if __name__ == '__main__':
    unittest.main()
