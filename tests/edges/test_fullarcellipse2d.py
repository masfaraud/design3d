import unittest
import design3d
import design3d.edges as d3de
from design3d import curves


class TestFullArcEllipse2D(unittest.TestCase):
    start_end = design3d.Point2D(0.0225, 0.0)
    major_axis = 0.0225
    minor_axis = 0.0075
    center = design3d.O2D
    major_dir = design3d.X2D
    ellispe2d = curves.Ellipse2D(major_axis, minor_axis, design3d.OXY)
    fullarcellipse = d3de.FullArcEllipse2D(ellispe2d, start_end)

    def test_init(self):
        self.assertAlmostEqual(self.fullarcellipse.ellipse.major_axis, 0.0225, places=4)
        self.assertAlmostEqual(self.fullarcellipse.ellipse.minor_axis, 0.0075, places=4)
        self.assertEqual(self.fullarcellipse.theta, 0.0)

    def test_length(self):
        self.assertAlmostEqual(self.fullarcellipse.length(), 0.10023669584870037)

    def test_to_3d(self):
        plane_origin = design3d.Point3D(1, 1, 1)
        x = design3d.Y3D
        y = design3d.Z3D
        ellipse3d = self.fullarcellipse.to_3d(plane_origin, x, y)
        self.assertEqual(ellipse3d.ellipse.major_dir, x)
        self.assertEqual(ellipse3d.ellipse.minor_dir, y)
        self.assertEqual(ellipse3d.normal, design3d.X3D)
        self.assertAlmostEqual(ellipse3d.ellipse.major_axis, 0.0225, places=4)
        self.assertAlmostEqual(ellipse3d.ellipse.minor_axis, 0.0075, places=4)

    def test_reverse(self):
        reverse = self.fullarcellipse.reverse()
        self.assertEqual(self.fullarcellipse.ellipse.frame.v.dot(reverse.ellipse.frame.v), -1)

    def test_frame_mapping(self):
        new_frame = design3d.Frame2D(design3d.O2D, -design3d.Y2D, design3d.X2D)
        new_ellipse = self.fullarcellipse.frame_mapping(new_frame, 'new')
        self.assertEqual(new_ellipse.ellipse.major_dir, design3d.Vector2D(0.0, 1.0))
        self.assertEqual(new_ellipse.ellipse.minor_dir, design3d.Vector2D(-1.0, 0.0))

    def test_abscissa(self):
        point1 = design3d.Point2D(0, -0.0075)
        point2 = design3d.Point2D(0.0225, 0)
        self.assertAlmostEqual(self.fullarcellipse.abscissa(point1), 0.75*self.fullarcellipse.length())
        self.assertAlmostEqual(self.fullarcellipse.abscissa(point2), 0.0)

        ellipse = d3de.FullArcEllipse2D(curves.Ellipse2D(0.000500289037421, 0.00050027520242, design3d.OXY),
                                       design3d.Point2D(0.0005002890374210534, 0))
        point = design3d.Point2D(-0.00018416867811365376, 0.00046514411968310123)
        self.assertAlmostEqual(ellipse.abscissa(point), 0.00098248885770749, 4)

    def test_translation(self):
        translated_ellipse = self.fullarcellipse.translation(design3d.X2D)
        self.assertEqual(translated_ellipse.ellipse.center, design3d.Point2D(1, 0))
        self.assertEqual(translated_ellipse.start_end, design3d.Point2D(1.0225, 0))


if __name__ == '__main__':
    unittest.main()
