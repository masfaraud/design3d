import math
import unittest

import volmdlr
from volmdlr import edges, faces, surfaces, wires
from dessia_common.core import DessiaObject


class TestCylindricalFace3D(unittest.TestCase):
    cylindrical_surface1 = surfaces.CylindricalSurface3D(volmdlr.OXYZ, 0.32)
    cylindrical_face1 = faces.CylindricalFace3D.from_surface_rectangular_cut(
        cylindrical_surface1, -0.01, 1.3, -0.1, 0.3)

    cylindrical_surface2 = surfaces.CylindricalSurface3D(volmdlr.OXYZ, 12.0)
    cylindrical_face2 = faces.CylindricalFace3D.from_surface_rectangular_cut(cylindrical_surface2, 0, 3.14, 0., 8.)

    def test_linesegment_intersections(self):
        lineseg3d = edges.LineSegment3D(volmdlr.O3D, volmdlr.Point3D(0.3, 0.3, .3))
        line_inters = self.cylindrical_face1.linesegment_intersections(lineseg3d)
        self.assertEqual(len(line_inters), 1)
        self.assertTrue(line_inters[0].is_close(volmdlr.Point3D(0.22627416, 0.22627416, 0.22627416)))
        cylindrical_face1 = faces.CylindricalFace3D.from_surface_rectangular_cut(
            self.cylindrical_surface1, -math.pi / 4, 1.5 * math.pi, -0.1, 0.3)
        lineseg3d_2 = edges.LineSegment3D(volmdlr.Point3D(-0.3, -0.3, -.1), volmdlr.Point3D(0.3, 0.3, .3))
        line_inters_2 = cylindrical_face1.linesegment_intersections(lineseg3d_2)
        self.assertEqual(len(line_inters_2), 2)
        self.assertTrue(line_inters_2[0].is_close(volmdlr.Point3D(0.2262741, 0.2262741, 0.2508494)))
        self.assertTrue(line_inters_2[1].is_close(volmdlr.Point3D(-0.2262741, -0.2262741, -0.0508494)))

    def test_triangulation_quality(self):
        """
        The triangle middle of triangulation should be at least at radius/20 of the surface
        """
        triangulation = self.cylindrical_face2.triangulation()
        # ax = self.cylindrical_surface2.plot()
        for i1, i2, i3 in triangulation.triangles:
            point1 = triangulation.points[i1]
            point2 = triangulation.points[i2]
            point3 = triangulation.points[i3]

            triangle = faces.Triangle3D(point1, point2, point3)
            # triangle.plot(ax=ax)
            # Test orthogonality
            self.assertAlmostEqual(triangle.surface3d.frame.w.dot(point1 - point2), 0.)
            # Test distance from middle to surface

            # if self.cylindrical_surface2.point_distance(triangle.middle()) < self.cylindrical_surface2.radius*0.05:
            #     triangle.middle().plot(ax=ax, color='g')
            # else:
            #     triangle.middle().plot(ax=ax, color='r')

            self.assertLess(self.cylindrical_surface2.point_distance(triangle.middle()),
                            self.cylindrical_surface2.radius * 0.05)

    def test_from_contours3d(self):
        surface = surfaces.CylindricalSurface3D.load_from_file(
            "faces/objects_cylindrical_tests/surface_openned_one_contour.json")
        contour3d_0 = wires.Contour3D.load_from_file(
            "faces/objects_cylindrical_tests/contour3d__openned_one_contour_0.json")
        contour3d_1 = wires.Contour3D.load_from_file(
            "faces/objects_cylindrical_tests/contour3d__openned_one_contour_1.json")

        contours = [contour3d_0, contour3d_1]
        face = faces.CylindricalFace3D.from_contours3d(surface, contours)
        self.assertAlmostEqual(face.surface2d.area(), 0.4272566008882119, 6)
        self.assertTrue(face.surface2d.outer_contour.is_ordered())

        surface = surfaces.CylindricalSurface3D.load_from_file(
            "faces/objects_cylindrical_tests/cylindrical_surface_repair_contour2d.json")
        contour3d_0 = wires.Contour3D.load_from_file(
            "faces/objects_cylindrical_tests/cylindrical_contour_0_repair_contour2d.json")
        contour3d_1 = wires.Contour3D.load_from_file(
            "faces/objects_cylindrical_tests/cylindrical_contour_1_repair_contour2d.json")

        contours = [contour3d_0, contour3d_1]
        face = faces.CylindricalFace3D.from_contours3d(surface, contours)
        self.assertAlmostEqual(face.surface2d.area(), 0.024190263432641437, 4)
        self.assertTrue(face.surface2d.outer_contour.is_ordered())

        surface = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/surface3d_1.json')
        contour0 = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/contour_1_0.json')
        contour1 = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/contour_1_1.json')

        face = faces.CylindricalFace3D.from_contours3d(surface, [contour0, contour1])

        self.assertEqual(face.surface2d.area(), 0.00077 * 2 * math.pi)

        frame = volmdlr.Frame3D(volmdlr.O3D, volmdlr.X3D, volmdlr.Y3D, volmdlr.Z3D)
        cylindrical = surfaces.CylindricalSurface3D(frame, 0.2)
        fullarc1 = edges.FullArc3D.from_center_normal(
            center=volmdlr.O3D, start_end=volmdlr.Point3D(0.2, 0.0, 0.0), normal=volmdlr.Z3D)
        fullarc2 = edges.FullArc3D.from_center_normal(
            center=volmdlr.O3D, start_end=volmdlr.Point3D(-0.2, 0.0, 0.2), normal=volmdlr.Z3D)
        contour1 = wires.Contour3D([fullarc1])
        contour2 = wires.Contour3D([fullarc2])
        face = faces.CylindricalFace3D.from_contours3d(cylindrical, [contour1, contour2])
        self.assertEqual(face.surface2d.area(), 0.2 * 2 * math.pi)

        surface = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/cylindrical_surface_floating_point_error.json')
        contour0 = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/cylindrical_contour_floating_point_error.json')

        face = faces.CylindricalFace3D.from_contours3d(surface, [contour0])
        self.assertTrue(face.surface2d.outer_contour.is_ordered())
        self.assertAlmostEqual(face.surface2d.area(), 0.003143137591511259, 3)

    def test_neutral_fiber(self):
        face = self.cylindrical_face1
        neutral_fiber = face.neutral_fiber()
        self.assertEqual(neutral_fiber.length(), 0.4)

    def test_number_triangles(self):
        cylindrical_surface1 = surfaces.CylindricalSurface3D(volmdlr.OXYZ, 0.32)
        cylindrical_face1 = faces.CylindricalFace3D.from_surface_rectangular_cut(cylindrical_surface1,
                                                                                 -0.01, 1.3, -0.1, 0.3)
        triangulation = cylindrical_face1.triangulation()
        triangulation.plot()
        n_triangles = len(triangulation.triangles)
        n_triangles_max = 30  # Could be 14 (7 slices on theta)
        self.assertLess(n_triangles, n_triangles_max,
                        f'Too much triangles in cylindrical face triangulation: {n_triangles}/{n_triangles_max}')

    def test_split_by_plane(self):
        R = 0.15
        cylindricalsurface = surfaces.CylindricalSurface3D(volmdlr.OXYZ, R)
        cylindricalface = faces.CylindricalFace3D.from_surface_rectangular_cut(cylindricalsurface, 0, volmdlr.TWO_PI,
                                                                               -.25, .25)
        plane_face_cylindricalface_intersec = DessiaObject.load_from_file(
            'faces/plane_face_cylindrical_face_intersec.json')
        plane_face_3 = plane_face_cylindricalface_intersec.rotation(volmdlr.O3D, volmdlr.X3D, math.pi / 7)
        split_by_plane = cylindricalface.split_by_plane(plane_face_3.surface3d)
        self.assertTrue(len(split_by_plane), 4)
        list_expected_points = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/test_cylindrical_faces_split_by_plane_'
            'expected_discretization_points.json').primitives
        for i, face in enumerate(split_by_plane):
            points = face.outer_contour3d.discretization_points(number_points=10)
            for point, expected_point in zip(points, list_expected_points[i]):
                self.assertTrue(point.is_close(expected_point))

    def test_plane_intersections(self):
        face, plane = DessiaObject.load_from_file(
            'faces/objects_cylindrical_tests/test_buggy_split_by_plane12_07_2023.json').primitives
        plane_intersections = face.plane_intersections(plane)
        self.assertAlmostEqual(plane_intersections[0].length(), 0.10485331158773475)

    def test_conicalface_intersections(self):
        expected_results = [[[3.710002373020358], [2.7546701820620956, 0.7935213268610651],
                             [2.075126659615459, 0.49133092704442394, 1.0377142838361861, 0.5464208526645894],
                             [2.5645345026338227, 2.5645345026338213], [0.544055470762666, 0.04555225339913864,
                                                                        1.2782308617047107, 0.2561660954970303]],
                            [[0.9041805829899517, 1.3797833276615086], [2.7546701820620956, 0.7935213268610651],
                             [0.9945099057847868, 0.011885786063087272, 0.49133092704442394, 1.0377142838361861,
                              0.5464208526645894],
                             [0.28956380719439634, 0.9392209120999059, 2.5645345026338213],
                             [0.2798809806923827, 0.045552253399138556, 0.7579657254386307]],
                            [[0.8560429148647001, 0.32222894295393023], [0.6888878304141478, 0.6888878304141477,
                                                                         0.1984154944167925, 0.19841549441679263],
                             [0.49133092704442394, 1.0377142838361861, 0.5464208526645894],
                             [2.5645345026338213],
                             []]]
        conical_surface = surfaces.ConicalSurface3D(volmdlr.OXYZ, math.pi / 6)
        conical_face = faces.ConicalFace3D.from_surface_rectangular_cut(
            conical_surface, 0, volmdlr.TWO_PI, 0, 2)

        cylindrical_surface1 = surfaces.CylindricalSurface3D(volmdlr.Frame3D(volmdlr.Point3D(.3, .3, 0.8),
                                                                             volmdlr.Y3D, volmdlr.Z3D, volmdlr.X3D),
                                                             0.3)
        cylindrical_surface2 = surfaces.CylindricalSurface3D(volmdlr.Frame3D(volmdlr.Point3D(0, 0, 0.5),
                                                                             volmdlr.Y3D, volmdlr.Z3D, volmdlr.X3D),
                                                             0.3)
        cylindrical_surface3 = surfaces.CylindricalSurface3D(volmdlr.Frame3D(volmdlr.Point3D(0, 0, 1),
                                                                             volmdlr.Y3D, volmdlr.Z3D, volmdlr.X3D),
                                                             0.3)
        point = volmdlr.Point3D(0, math.tan(conical_surface.semi_angle), 1)
        normal = volmdlr.Vector3D(0.0, -0.5773502691896256, 1.0)
        center = point + normal * math.tan(conical_surface.semi_angle) / 2
        cylindrical_surface4 = surfaces.CylindricalSurface3D(volmdlr.Frame3D(center,
                                                                             volmdlr.Y3D, volmdlr.Z3D, volmdlr.X3D),
                                                             math.tan(conical_surface.semi_angle) / 2)
        vector1 = volmdlr.Vector3D(1, 1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        vector3 = vector1.cross(vector2)
        frame = volmdlr.Frame3D(volmdlr.O3D, vector1, vector2, vector3)
        cylindrical_surface5 = surfaces.CylindricalSurface3D(frame, math.tan(conical_surface.semi_angle) / 2)

        for i, z in enumerate([-1, -0.5, 0]):
            for j, cylindrical_surface in enumerate([cylindrical_surface1, cylindrical_surface2, cylindrical_surface3,
                                                     cylindrical_surface4, cylindrical_surface5]):
                cyl_face = faces.CylindricalFace3D.from_surface_rectangular_cut(
                    cylindrical_surface, 0, volmdlr.TWO_PI, z, 2)
                list_curves = cyl_face.face_intersections(conical_face)
                for curve_solution, expected_result in zip(list_curves, expected_results[i][j]):
                    self.assertAlmostEqual(curve_solution.length(), expected_result)


if __name__ == '__main__':
    unittest.main()
