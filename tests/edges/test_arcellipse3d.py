import math
import unittest
from itertools import product

import design3d
from design3d import edges, curves


class TestArcEllipse3D(unittest.TestCase):
    vector1 = design3d.Vector3D(1, 1, 1)
    vector1 = vector1.unit_vector()
    vector2 = vector1.deterministic_unit_normal_vector()
    vector3 = vector1.cross(vector2)
    ellipse3d = curves.Ellipse3D(2, 1, design3d.Frame3D(design3d.O3D, vector1, vector2, vector3))
    arc_ellipse3d = edges.ArcEllipse3D(
        ellipse3d,
        start=design3d.Point3D(0.2391463117381003, 1.1051717155225391, 1.1051717155225391),
        end=design3d.Point3D(-1.393846850117352, -0.5278214463329132, -0.5278214463329132))
    discretization_points = arc_ellipse3d.discretization_points(number_points=6)

    def test_init(self):
        expected_lengths = [0.9656637, 2.4221121, 3.8785604, 4.8442241, 5.8098879, 7.2663362, 8.7227845, 8.7227845,
                            1.4564483, 2.9128966, 3.8785604, 4.8442241, 6.3006724, 7.7571207, 8.7227845, 7.2663362,
                            8.2319999, 1.4564483, 2.4221121, 3.3877758, 4.8442241, 6.3006724, 7.2663362, 5.8098879,
                            6.7755516, 8.2319999, 0.9656637, 1.9313275, 3.3877758, 4.8442241, 5.8098879, 4.8442241,
                            5.8098879, 7.2663362, 8.7227845, 0.9656637, 2.4221121, 3.8785604, 4.8442241, 3.8785604,
                            4.8442241, 6.3006724, 7.7571207, 8.7227845, 1.4564483, 2.9128966, 3.8785604, 2.4221121,
                            3.3877758, 4.8442241, 6.3006724, 7.2663362, 8.2319999, 1.4564483, 2.4221121, 0.9656637,
                            1.9313275, 3.3877758, 4.8442241, 5.8098879, 6.7755516, 8.2319999, 0.9656637, 0.9656637,
                            2.4221121, 3.8785604, 4.8442241, 5.8098879, 7.2663362, 8.7227845]
        list_lengths = []
        for point1, point2 in product(self.ellipse3d.discretization_points(number_points=9), repeat=2):
            if not point1.is_close(point2):
                arc_ellipse3d = edges.ArcEllipse3D(self.ellipse3d, start=point1, end=point2)
                list_lengths.append(round(arc_ellipse3d.length(), 7))
        for length, expected_length in zip(list_lengths, expected_lengths):
            self.assertAlmostEqual(length, expected_length)

    def test_length(self):
        self.assertAlmostEqual(self.arc_ellipse3d.length(), 6.775551598718291)

    def test_discretization_points(self):
        expected_points = [design3d.Point3D(0.2391463117381003, 1.1051717155225391, 1.1051717155225391),
                           design3d.Point3D(1.2682124644807213, 1.0766201557138122, 1.0766201557138122),
                           design3d.Point3D(1.2517268550524192, 0.1604711841762696, 0.1604711841762696),
                           design3d.Point3D(0.20328070611577842, -0.8879749647603705, -0.8879749647603705),
                           design3d.Point3D(-1.0127560527915094, -1.2043483615584183, -1.2043483615584183),
                           design3d.Point3D(-1.3938468501173518, -0.5278214463329127, -0.5278214463329127)]

        for expected_point, point in zip(expected_points, self.discretization_points):
            self.assertTrue(expected_point.is_close(point))
        expected_points = [design3d.Point3D(0.029550000005800003, 0.0, 0.003949999999400002),
                           design3d.Point3D(0.029610009381392667, -0.0006859103016802056, 0.003889990623807338),
                           design3d.Point3D(0.029788214153659485, -0.001350979565931198, 0.0037117858515405226),
                           design3d.Point3D(0.03007919966077109, -0.0019749999997000166, 0.0034208003444289163),
                           design3d.Point3D(0.030474124455339677, -0.002539011057876173, 0.0030258755498603343),
                           design3d.Point3D(0.030960988947323857, -0.003025875549860349, 0.0025390110578761556),
                           design3d.Point3D(0.031525000005500015, -0.0034208003444289267, 0.0019749999996999975),
                           design3d.Point3D(0.03214902043926884, -0.0037117858515405286, 0.0013509795659311767),
                           design3d.Point3D(0.03281408970351983, -0.00388999062380734, 0.0006859103016801831),
                           design3d.Point3D(0.0335000000052, -0.0039499999993999994, 3.095745883019e-18)]
        vec1 = design3d.Vector3D(-0.7071067811865476, 0.0, 0.7071067811865476)
        vec2 = design3d.Vector3D(0.0, -1.0, 0.0)
        vec3 = vec1.cross(vec2)
        arc_ellipse3d_2 = edges.ArcEllipse3D(
            curves.Ellipse3D(0.005586143570525195, 0.0039499999993999994, design3d.Frame3D(
                design3d.Point3D(0.0335000000052, 0.0, 0.0), vec1, vec2, vec3)),
            design3d.Point3D(0.029550000005800003, 0.0, 0.0039499999994),
            design3d.Point3D(0.0335000000052, -0.0039499999994, 0.0))
        discretization_points = arc_ellipse3d_2.discretization_points(number_points=10)
        self.assertEqual(len(discretization_points), 10)
        for expected_point, point in zip(expected_points, discretization_points):
            self.assertTrue(expected_point.is_close(point))

    def test_reverse(self):
        arc_ellipse3d_reverse = self.arc_ellipse3d.reverse()
        self.assertTrue(arc_ellipse3d_reverse.start.is_close(self.arc_ellipse3d.end))
        self.assertTrue(arc_ellipse3d_reverse.end.is_close(self.arc_ellipse3d.start))
        self.assertAlmostEqual(arc_ellipse3d_reverse.length(), self.arc_ellipse3d.length())

    def test_complementary(self):
        arc_ellipse3d_complementary = self.arc_ellipse3d.complementary()
        self.assertTrue(arc_ellipse3d_complementary.start.is_close(self.arc_ellipse3d.end))
        self.assertTrue(arc_ellipse3d_complementary.end.is_close(self.arc_ellipse3d.start))
        self.assertAlmostEqual(self.arc_ellipse3d.length() + arc_ellipse3d_complementary.length(),
                               self.arc_ellipse3d.ellipse.length())

    def test_abscissa(self):
        expected_abcissas = [0, 1.1246510017713454, 2.4709452498238225,
                             4.304606348894478, 5.650900596946949, 6.775551598718295]
        abscissas = [self.arc_ellipse3d.abscissa(point) for point in self.discretization_points]
        for abscissa, expected_abcissa in zip(abscissas, expected_abcissas):
            self.assertAlmostEqual(abscissa, expected_abcissa)

    def test_point_at_abscissa(self):
        abscissas = [self.arc_ellipse3d.abscissa(point) for point in self.discretization_points]
        points_at_abscissas = [self.arc_ellipse3d.point_at_abscissa(abscissa) for abscissa in abscissas]
        for discr_pt, point in zip(self.discretization_points, points_at_abscissas):
            self.assertTrue(discr_pt.is_close(point))

    def test_point_belongs(self):
        self.assertTrue(self.arc_ellipse3d.point_belongs(self.discretization_points[2]))
        self.assertFalse(self.arc_ellipse3d.point_belongs(
            design3d.Point3D(-0.816496580927726, 0.40824829046386313, 0.40824829046386313)))

    def test_translation(self):
        translated_arc_ellipse3d = self.arc_ellipse3d.translation(self.arc_ellipse3d.ellipse.frame.w)
        self.assertTrue(translated_arc_ellipse3d.start.is_close(
            design3d.Point3D(0.2391463117381003, 1.8122784967090868, 0.39806493433599155)))
        self.assertTrue(translated_arc_ellipse3d.end.is_close(
            design3d.Point3D(-1.393846850117352, 0.1792853348536344, -1.2349282275194606)))
        self.assertAlmostEqual(self.arc_ellipse3d.length(), translated_arc_ellipse3d.length())

    def test_rotation(self):
        rotated_arc_ellipse3d = self.arc_ellipse3d.rotation(
            design3d.O3D,self.arc_ellipse3d.ellipse.frame.v, math.pi / 2)
        self.assertTrue(rotated_arc_ellipse3d.start.is_close(
            design3d.Point3D(-0.577350269189626, -0.7113248654051868, 1.288675134594813)))
        self.assertTrue(rotated_arc_ellipse3d.end.is_close(
            design3d.Point3D(-0.5773502691896256, 1.2886751345948129, -0.7113248654051871)))
        self.assertAlmostEqual(self.arc_ellipse3d.length(), rotated_arc_ellipse3d.length())

    def test_frame_mapping(self):
        frame_mapped_arc_ellipse3d = self.arc_ellipse3d.frame_mapping(self.arc_ellipse3d.ellipse.frame, 'new')
        self.assertTrue(frame_mapped_arc_ellipse3d.start.is_close(
            design3d.Point3D(1.414213562373095, -0.7071067811865475, 0.0)))
        self.assertTrue(frame_mapped_arc_ellipse3d.end.is_close(
            design3d.Point3D(-1.414213562373095, -0.7071067811865475, 0.0)))
        self.assertAlmostEqual(self.arc_ellipse3d.length(), frame_mapped_arc_ellipse3d.length())

    def test_direction_vector(self):
        direction_vector = self.arc_ellipse3d.direction_vector(
            self.arc_ellipse3d.abscissa(self.discretization_points[2]))
        self.assertTrue(direction_vector.is_close(
            design3d.Point3D(0.36933737285964724, 0.6813567173546152, 0.6813567173546152)))

    def test_normal_vector(self):
        normal_vector = self.arc_ellipse3d.normal_vector(
            self.arc_ellipse3d.abscissa(self.discretization_points[2]))
        self.assertTrue(
            normal_vector.is_close(design3d.Point3D(0.8719038343714461, -0.23631286251473488, -0.23631286251473488)))

    def test_split(self):
        split = self.arc_ellipse3d.split(self.discretization_points[2])
        self.assertEqual(len(split), 2)
        self.assertTrue(split[0].start.is_close(self.arc_ellipse3d.start))
        self.assertTrue(split[0].end.is_close(self.discretization_points[2]))
        self.assertTrue(split[1].start.is_close(self.discretization_points[2]))
        self.assertTrue(split[1].end.is_close(self.arc_ellipse3d.end))

    def test_linesegment_intersections(self):
        lineseg1 = edges.LineSegment3D(
            design3d.Point3D(2.548547388496604, 3.4145727922810423, 3.4145727922810423),
            design3d.Point3D(-1.6329931618554527, -3.36504396942433, -3.36504396942433))
        lineseg2 = edges.LineSegment3D(
            design3d.Point3D(-0.5978657793452512, -2.7629292888063484, -1.2103434310450787),
            design3d.Point3D(0.47829262347620083, 2.2103434310450787, -0.8948282844774607))
        lineseg3 = edges.LineSegment3D(design3d.Point3D(3.0, 4.0, 2.5),
                                       design3d.Point3D(-3.0, -5.0, -2.0))
        expected_results = [
            [design3d.Point3D(-0.23914631173810008, -1.105171715522539, -1.105171715522539),
             design3d.Point3D(1.154700538379252, 1.1547005383792517, 1.1547005383792517)],
            [design3d.Point3D(-0.2391463117381003, -1.1051717155225391, -1.1051717155225391)],
            []
        ]
        for i, lineseg in enumerate([lineseg1, lineseg2, lineseg3]):
            intersections = self.arc_ellipse3d.linesegment_intersections(lineseg)
            for result, expected_result in zip(intersections[::-1], expected_results[i]):
                self.assertTrue(result.is_close(expected_result))

    def test_arc_intersections(self):
        arc1 = edges.Arc3D.from_3_points(
            design3d.Point3D(-3.3288684211090134, -0.5435060060274549, -0.5435060060274549),
            design3d.Point3D(0.4007646643644225, -0.8377597481168791, -0.8377597481168791),
            design3d.Point3D(0.8169022928215985, 1.799489070171162, 1.799489070171162)
        )
        arc2 = edges.Arc3D.from_3_points(
            design3d.Point3D(1.3588246836111835, 0.8491831845891217, 0.39006834315301087),
            design3d.Point3D(1.255568331576755, 0.5696474190625116, 1.2109400610588277),
            design3d.Point3D(1.2199886174598773, 1.2728187935178512, 0.6943003434687043)
        )
        expected_intersections1 = [design3d.Point3D(1.354577913713, 0.964620364538, 0.964620364538),
                                   design3d.Point3D(1.393846848023, 0.527821436653, 0.527821436653),
                                   design3d.Point3D(-0.239145968544, -1.105171585562, -1.105171585562),
                                   design3d.Point3D(-0.83463441314, -1.224592065711, -1.224592065711)]
        expected_intersections2 = [design3d.Point3D(1.3938468501173522, 0.5278214463329128, 0.5278214463329132),
                                   design3d. Point3D(1.1547005383792521, 1.1547005383792512, 1.1547005383792517)]
        intersections1 = arc1.arcellipse_intersections(self.arc_ellipse3d)
        intersections2 = arc2.arcellipse_intersections(self.arc_ellipse3d)
        for result, expected_result in zip(intersections1, expected_intersections1):
            self.assertTrue(result.is_close(expected_result))
        for result, expected_result in zip(intersections2, expected_intersections2):
            self.assertTrue(result.is_close(expected_result))

    def test_arcellipse(self):
        arc_ellipse3d_2 = self.arc_ellipse3d.translation(self.ellipse3d.frame.u * 0.2)
        arc_ellipse3d_2 = arc_ellipse3d_2.rotation(self.ellipse3d.center, self.ellipse3d.frame.w, math.pi / 3)
        arcellipse_intersections = self.arc_ellipse3d.arcellipse_intersections(arc_ellipse3d_2)
        self.assertEqual(len(arcellipse_intersections), 1)
        self.assertTrue(arcellipse_intersections[0].is_close(
            design3d.Point3D(0.442026341769, -0.728884874076, -0.728884874076)))

    def test_is_close(self):
        self.assertTrue(self.arc_ellipse3d.is_close(self.arc_ellipse3d))


if __name__ == '__main__':
    unittest.main()
