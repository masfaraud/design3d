import math
import unittest
import os

import volmdlr
import volmdlr.edges as vme
from volmdlr import curves, surfaces, edges
import volmdlr.wires as vmw
from volmdlr import O3D, X3D, Y3D, Z3D, Point2D, Point3D
from volmdlr.models import conical_surfaces


folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'objects_conical_tests')


class TestConicalSurface3D(unittest.TestCase):
    conical_surface = conical_surfaces.conical_surface1
    conical_surface2 = conical_surfaces.conical_surface2

    def test_arc3d_to_2d(self):
        arc1 = vme.Arc3D.from_3_points(volmdlr.Point3D(-1 / math.sqrt(2), 1 / math.sqrt(2), 1 / math.sqrt(3)),
                         volmdlr.Point3D(-1, 0, 1 / math.sqrt(3)),
                         volmdlr.Point3D(-1 / math.sqrt(2), -1 / math.sqrt(2), 1 / math.sqrt(3)))
        arc2 = vme.Arc3D.from_3_points(volmdlr.Point3D(0, -1, 1 / math.sqrt(3)),
                         volmdlr.Point3D(-1 / math.sqrt(2), 1 / math.sqrt(2), 1 / math.sqrt(3)),
                         volmdlr.Point3D(1, 0, 1 / math.sqrt(3)))
        test1 = self.conical_surface.arc3d_to_2d(arc3d=arc1)[0]
        test2 = self.conical_surface.arc3d_to_2d(arc3d=arc2)[0]

        # Assert that the returned object is an edges.LineSegment2D
        self.assertIsInstance(test1, vme.LineSegment2D)
        self.assertIsInstance(test2, vme.LineSegment2D)

        # Assert that the returned object is right on the parametric domain (take into account periodicity)
        self.assertTrue(test1.start.is_close(volmdlr.Point2D(0.75 * math.pi, 0.5773502691896258)))
        self.assertTrue(test1.end.is_close(volmdlr.Point2D(1.25 * math.pi, 0.5773502691896258)))
        self.assertTrue(test2.start.is_close(volmdlr.Point2D(-0.5 * math.pi, 0.5773502691896258)))
        self.assertTrue(test2.end.is_close(volmdlr.Point2D(-2 * math.pi, 0.5773502691896258)))

    def test_contour2d_to_3d(self):
        contour2d = vmw.Contour2D([vme.LineSegment2D(volmdlr.Point2D(-math.pi, 0.0), volmdlr.Point2D(math.pi, 0.0)),
                                   vme.LineSegment2D(volmdlr.Point2D(math.pi, 0.0), volmdlr.Point2D(math.pi, 1.0)),
                                   vme.LineSegment2D(volmdlr.Point2D(math.pi, 1.0), volmdlr.Point2D(-math.pi, 1.0)),
                                   vme.LineSegment2D(volmdlr.Point2D(-math.pi, 1.0), volmdlr.Point2D(-math.pi, 0.0))])
        contour3d, primitives_mapping = self.conical_surface.contour2d_to_3d(contour2d, return_primitives_mapping=True)
        self.assertEqual(len(contour3d.primitives), len(primitives_mapping))
        self.assertIsNone(primitives_mapping.get(contour2d.primitives[0]))
        self.assertEqual(contour3d.primitives[0], primitives_mapping[contour2d.primitives[1]])
        self.assertEqual(contour3d.primitives[1], primitives_mapping[contour2d.primitives[2]])
        self.assertEqual(contour3d.primitives[2], primitives_mapping[contour2d.primitives[3]])

    def test_contour3d_to_2d(self):
        center1 = O3D
        start_end1 = Point3D(0.035, 0, 0)
        circle1 = curves.Circle3D(volmdlr.Frame3D(center1, volmdlr.X3D, volmdlr.Y3D, volmdlr.Z3D),
                                  center1.point_distance(start_end1))
        primitives_cone = [vme.LineSegment3D(Point3D(0, 0, 0.1), Point3D(0.035, 0, 0.0)),
                           vme.FullArc3D(circle1, start_end1),
                           vme.LineSegment3D(Point3D(0.035, 0, 0.0), Point3D(0, 0, 0.1))]

        primitives_demi_cone = [primitives_cone[0],
                                vme.Arc3D.from_3_points(Point3D(0.035, 0, 0),
                                                        Point3D(0, 0.035, 0), Point3D(-0.035, 0, 0)),
                                vme.LineSegment3D(Point3D(-0.035, 0, 0.0), Point3D(0, 0, 0.1))
                                ]

        contour_cone = vmw.Contour3D(primitives_cone)
        contour2d_cone = self.conical_surface2.contour3d_to_2d(contour_cone)

        contour_demi_cone = vmw.Contour3D(primitives_demi_cone)
        contour2d_demi_cone = self.conical_surface2.contour3d_to_2d(contour_demi_cone)

        area_cone = contour2d_cone.area()
        area_demi_cone = contour2d_demi_cone.area()
        fullarc2d = contour2d_cone.primitives[1]
        linesegment2d_cone = contour2d_cone.primitives[2]

        # Assert that the returned object is an edges.LineSegment2D
        self.assertIsInstance(fullarc2d, vme.LineSegment2D)
        self.assertIsInstance(linesegment2d_cone, vme.LineSegment2D)

        self.assertEqual(area_cone, 0.2 * math.pi)
        self.assertEqual(area_demi_cone, 0.1 * math.pi)
        self.assertEqual(fullarc2d.start, Point2D(0, 0.1))
        self.assertEqual(fullarc2d.end, Point2D(-2 * math.pi, 0.1))
        self.assertEqual(fullarc2d.length(), 2 * math.pi)
        self.assertEqual(linesegment2d_cone.start, Point2D(-2 * math.pi, 0.1))
        self.assertEqual(linesegment2d_cone.end, Point2D(-2 * math.pi, 0.0))

        surface = surfaces.ConicalSurface3D.from_json(os.path.join(folder, "conical_singularity_suface.json"))
        contour3d = vmw.Contour3D.from_json(os.path.join(folder, "conical_singularity_contour.json"))
        contour, primitives_mapping = surface.contour3d_to_2d(contour3d, return_primitives_mapping=True)
      
        self.assertTrue(contour.is_ordered())
        self.assertAlmostEqual(contour.area(), 0.0025393181156878604, 6)
        self.assertEqual(len(primitives_mapping), len(contour3d.primitives))
        self.assertIsNone(primitives_mapping.get(contour.primitives[3]))
        self.assertEqual(contour3d.primitives[0], primitives_mapping.get(contour.primitives[0]))
        self.assertEqual(contour3d.primitives[1], primitives_mapping.get(contour.primitives[1]))
        self.assertEqual(contour3d.primitives[2], primitives_mapping.get(contour.primitives[2]))


        surface = surfaces.ConicalSurface3D.from_json(
            os.path.join(folder, "conicalsurface_contour_with_singularity_2.json"))
        contour3d = vmw.Contour3D.from_json(
            os.path.join(folder, "conicalsurface_contour_with_singularity_contour_2.json"))
        contour = surface.contour3d_to_2d(contour3d)
        self.assertTrue(contour.is_ordered())
        self.assertAlmostEqual(contour.area(), math.pi * 0.0014073966802667698, 5)

        surface = surfaces.ConicalSurface3D.from_json(
            os.path.join(folder, "conicalsurface_linesegment3d_to_2d.json"))
        contour3d = vmw.Contour3D.from_json(
            os.path.join(folder, "conicalsurface_linesegment3d_to_2d_contour.json"))
        contour = surface.contour3d_to_2d(contour3d)
        self.assertTrue(contour.is_ordered())



    def test_bsplinecurve3d_to_2d(self):
        conical_surface3 = conical_surfaces.conical_surface3
        control_points = [volmdlr.Point3D(-0.00235270234694772, 0.004075, 0.000502294734194974),
                          volmdlr.Point3D(-0.00158643061573795, 0.004075, 0.000281091139051792),
                          volmdlr.Point3D(-1.38558964783719e-06, 0.004075, -4.49804036433251e-06),
                          volmdlr.Point3D(0.00158690018976903, 0.004075, 0.000281226693398416),
                          volmdlr.Point3D(0.00235270234694773, 0.004075, 0.000502294734194975)]

        bspline_curve = vme.BSplineCurve3D(3, control_points, [4, 1, 4], knots=[0.0, 0.5, 1.0])
        bspline_curve2d = conical_surface3.bsplinecurve3d_to_2d(bspline_curve)
        bspline_curve3d = conical_surface3.bsplinecurve2d_to_3d(bspline_curve2d[0])
        original_length = bspline_curve.length()
        length_after_transformation = bspline_curve3d[0].length()
        point = bspline_curve.point_at_abscissa(0.5*original_length)
        point_test = bspline_curve3d[0].point_at_abscissa(0.5 * length_after_transformation)
        self.assertAlmostEqual(original_length, length_after_transformation, places=6)
        self.assertTrue(point.is_close(point_test, 1e-6))

    def test_line_intersections(self):
        conical_surface = surfaces.ConicalSurface3D(volmdlr.OXYZ, math.pi / 6)

        lines = [curves.Line3D(volmdlr.Point3D(-2, -2, 1), volmdlr.Point3D(5, 5, 5)),
                 curves.Line3D(volmdlr.Point3D(1.1409943273101928, 1.1409943273101928, 2.7948539013201095),
                               volmdlr.Point3D(1.1409943273101928, 1.1409943273101928, 2.7948539013201095) +
                               2 * volmdlr.Vector3D(-0.9742215979209138, -0.15847358160064154, -0.0)),
                 curves.Line3D(volmdlr.Point3D(1, 1, 0), volmdlr.Point3D(2, -2, 5)),
                 curves.Line3D(volmdlr.Point3D(1, 1, 0), volmdlr.Point3D(2, 2, 5)),
                 curves.Line3D(volmdlr.Point3D(1, 1, 0), volmdlr.Point3D(0.0, 3.920784075149046, 4.801960187872612)),
                 curves.Line3D(volmdlr.Point3D(1.960392037574523, 1.960392037574523, 4.801960187872612),
                               volmdlr.Point3D(0.0, 3.920784075149046, 4.801960187872612))]
        list_intersections = [[Point3D(-0.7093396510512004, -0.7093396510512004, 1.7375201993993143),
                               Point3D(1.1409943273101928, 1.1409943273101928, 2.7948539013201095)],
                              [Point3D(1.1409943273076404, 1.1409943273121101, 2.7948539013193323),
                               Point3D(-1.443803221499384, 0.7205333909643816, 2.794853901319333)],
                              [Point3D(1.7101020514359682, -1.1303061543105355, 3.550510257187456),
                               Point3D(2.6898979485879435, -4.06969384577009, 8.449489742957839)],
                              [Point3D(1.960392037574523, 1.960392037574523, 4.801960187872612)],
                              [],
                              [Point3D(1.9603920375740307, 1.9603920375740307, 4.801960187873013)]]

        for i, line in enumerate(lines):
            line_intersections = conical_surface.line_intersections(line)
            for intersection, expected_sesult in zip(line_intersections, list_intersections[i]):
                self.assertTrue(intersection.is_close(expected_sesult))

    def test_plane_intersections(self):
        conical_surface = surfaces.ConicalSurface3D(volmdlr.OXYZ, math.pi / 6)

        plane1 = surfaces.Plane3D(volmdlr.Frame3D(volmdlr.Point3D(0, 0, 0.5),
                                                  volmdlr.X3D, volmdlr.Y3D, volmdlr.Z3D))
        plane2 = surfaces.Plane3D(volmdlr.Frame3D(volmdlr.Point3D(0, 0.25, 0.5),
                                                  volmdlr.Z3D, volmdlr.X3D, volmdlr.Y3D))
        plane3 = surfaces.Plane3D(volmdlr.Frame3D(volmdlr.Point3D(0, 0.0, 0.5),
                                                  volmdlr.Z3D, volmdlr.X3D, volmdlr.Y3D))
        vector1 = volmdlr.Vector3D(1, 1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        vector3 = vector1.cross(vector2)
        frame = volmdlr.Frame3D(volmdlr.Point3D(0, 0, 0.5), vector1, vector2, vector3)
        plane4 = surfaces.Plane3D(frame)
        point1 = conical_surface.frame.origin
        point2 = conical_surface.frame.local_to_global_coordinates(
            volmdlr.Point3D(10 * math.tan(conical_surface.semi_angle), 0, 10))
        generatrix = edges.LineSegment3D(point1, point2)
        normal = generatrix.unit_normal_vector()
        plane5 = surfaces.Plane3D.from_normal(frame.origin - normal * .5, normal)
        expected_results = [[('Circle3D', 0.2886751345948128)],
                            [('Hyperbola3D', 0.4330127018922194)],
                            [('Line3D', volmdlr.Point3D(-1.0, 0.0, 1.7320508075688776)),
                             ('Line3D', volmdlr.Point3D(1.0, 0.0, 1.7320508075688776))],
                            [('Ellipse3D', 0.3535533905927743)],
                            [('Parabola3D', 0.21650635094600354)]]
        for i, plane in enumerate([plane1, plane2, plane3, plane4, plane5]):
            intersections = conical_surface.surface_intersections(plane)
            for intersection, expected_result in zip(intersections, expected_results[i]):
                self.assertEqual(intersection.__class__.__name__, expected_result[0])
                if i == 2:
                    self.assertTrue(intersection[1].is_close(expected_result[1]))
                else:
                    self.assertAlmostEqual(intersection[1], expected_result[1])

    def test_ellipse_intersections(self):
        conical_surface = surfaces.ConicalSurface3D(
            volmdlr.Frame3D(origin=volmdlr.Point3D(1.0, 1.0, 0.0),
                            u=volmdlr.Vector3D(-5.551115123125783e-17, 0.0, 0.9999999999999998),
                            v=volmdlr.Vector3D(0.0, 0.9999999999999998, 0.0),
                            w=volmdlr.Vector3D(-0.9999999999999998, 0.0, -5.551115123125783e-17)), math.pi / 4)

        frame = volmdlr.Frame3D(origin=volmdlr.Point3D(0.0, 0.0, 0.0),
                                u=volmdlr.Vector3D(0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
                                v=volmdlr.Vector3D(0.8164965809277258, -0.40824829046386313, -0.40824829046386313),
                                w=volmdlr.Vector3D(0.0, 0.7071067811865476, -0.7071067811865476))
        ellipse = curves.Ellipse3D(2, 1, frame)
        ellipse_intersections = conical_surface.ellipse_intersections(ellipse)
        self.assertEqual(len(ellipse_intersections), 2)
        self.assertTrue(ellipse_intersections[0].is_close(
            volmdlr.Point3D(-1.2979434653952304, -1.0460502895587362, -1.0460502895587362)))
        self.assertTrue(ellipse_intersections[1].is_close(
            volmdlr.Point3D(-5.967998071287894e-07, 0.9999997016000061, 0.9999997016000058)))

    def test_arcellipse_intersections(self):
        conical_surface = surfaces.ConicalSurface3D(
            volmdlr.Frame3D(origin=volmdlr.Point3D(1.0, 1.0, 0.0),
                            u=volmdlr.Vector3D(-5.551115123125783e-17, 0.0, 0.9999999999999998),
                            v=volmdlr.Vector3D(0.0, 0.9999999999999998, 0.0),
                            w=volmdlr.Vector3D(-0.9999999999999998, 0.0, -5.551115123125783e-17)), math.pi / 4)
        frame = volmdlr.Frame3D(origin=volmdlr.Point3D(0.0, 0.0, 0.0),
                                u=volmdlr.Vector3D(0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
                                v=volmdlr.Vector3D(0.8164965809277258, -0.40824829046386313, -0.40824829046386313),
                                w=volmdlr.Vector3D(0.0, 0.7071067811865476, -0.7071067811865476))
        ellipse = curves.Ellipse3D(2, 1, frame)
        arcellipse = edges.ArcEllipse3D(ellipse, ellipse.point_at_abscissa(4.5), ellipse.point_at_abscissa(8.0))
        arcellipse_intersections = conical_surface.arcellipse_intersections(arcellipse)
        self.assertEqual(len(arcellipse_intersections), 1)
        self.assertTrue(arcellipse_intersections[0].is_close(
            volmdlr.Point3D(-1.2979434653952304, -1.0460502895587362, -1.0460502895587362)))

    def test_sphericalsurface_intersections(self):
        spherical_surface = surfaces.SphericalSurface3D(volmdlr.OXYZ.translation(volmdlr.Vector3D(0.5, 0.5, 0)),
                                                        2)

        # test 1
        conical_surface = surfaces.ConicalSurface3D(volmdlr.OXYZ, math.pi / 6)
        inters = spherical_surface.surface_intersections(conical_surface)
        self.assertEqual(len(inters), 1)
        self.assertAlmostEqual(inters[0].length(), 6.132194414411092)
        # test 2
        conical_surface = surfaces.ConicalSurface3D(volmdlr.OXYZ, math.pi / 6)
        conical_surface = conical_surface.translation(-volmdlr.Z3D * 2)
        inters = spherical_surface.surface_intersections(conical_surface)
        self.assertEqual(len(inters), 2)
        self.assertAlmostEqual(inters[0].length(), 10.905677051611681)
        self.assertAlmostEqual(inters[1].length(), 0.5120820085072879)


if __name__ == '__main__':
    unittest.main()
