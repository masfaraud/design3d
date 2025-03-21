import unittest

import design3d
from design3d import edges, curves


class TestFullArc3D(unittest.TestCase):
    center = design3d.Point3D(0.0, 0.0, -0.25)
    start_end = design3d.Point3D(0.15, 0.0, -0.25)
    circle = curves.Circle3D(design3d.Frame3D(center, design3d.X3D, design3d.Y3D, design3d.Z3D),
                             center.point_distance(start_end))
    fullarc3d = edges.FullArc3D(circle, start_end)

    def test_linesegment_intersections(self):
        line3d = edges.LineSegment3D(design3d.Point3D(-0.2, -0.2, -.25), design3d.Point3D(0.2, 0.2, -.25))
        line3d_ = edges.LineSegment3D(design3d.Point3D(-.15, 0, 0), design3d.Point3D(-0.15, 0.0, -.35))
        linesegment_intesections1 = self.fullarc3d.linesegment_intersections(line3d)
        self.assertEqual(len(linesegment_intesections1), 2)
        self.assertTrue(linesegment_intesections1[0].is_close(
            design3d.Point3D(0.10606601717798213, 0.10606601717798214, -0.25)))
        self.assertTrue(linesegment_intesections1[1].is_close(
                         design3d.Point3D(-0.10606601717798213, -0.10606601717798213, -0.25)))
        linesegment_intesections2 = self.fullarc3d.linesegment_intersections(line3d_)
        self.assertEqual(len(linesegment_intesections2), 1)
        self.assertEqual(linesegment_intesections2[0], design3d.Point3D(-0.15, 0.0, -0.25))

    def test_from_3_points(self):
        point1 = design3d.Point3D(607.597, 102.093550000191, 0.98)
        point2 = design3d.Point3D(607.597, 102.07645353018361, 0.9797543234978285)
        point3 = design3d.Point3D(607.597, 102.08536951838659, 0.9714579885610268)
        fullarc3d = edges.FullArc3D.from_3_points(point1, point2, point3)
        self.assertAlmostEqual(fullarc3d.circle.radius,  0.00855)
        self.assertAlmostEqual(fullarc3d.circle.normal.cross(design3d.X3D).norm(), 0)
        self.assertEqual(fullarc3d.angle, design3d.TWO_PI)

    def test_fullarc_intersections(self):
        fullarc3d_ = self.fullarc3d.rotation(self.center, design3d.X3D, 1.4)
        fullarc_intersections = fullarc3d_.fullarc_intersections(self.fullarc3d)
        self.assertEqual(len(fullarc_intersections), 2)
        self.assertTrue(fullarc_intersections[0], design3d.Point3D(0.1499999999999999, 0.0, -0.25))
        self.assertTrue(fullarc_intersections[1], design3d.Point3D(-0.1499999999999999, 0.0, -0.25))


if __name__ == '__main__':
    unittest.main()
