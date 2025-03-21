import unittest
import design3d
from design3d import curves, edges


class TestParabola2D(unittest.TestCase):
    def test_line_intersections(self):
        expected_results = [[[design3d.Point2D(0.43439728232830777, 4.150547925156083),
                              design3d.Point2D(-1407.1677289150666, 1283.7888444682421)],
                             [design3d.Point2D(0.0, 0.0),
                              design3d.Point2D(-1.2570787221094177, -0.6285393610547088)],
                             [design3d.Point2D(0.15914794847249425, 5.159147948472494),
                              design3d.Point2D(-5.159147948472494, -0.15914794847249425)]],
                            [[design3d.Point2D(2.8172904669025316, 1.984281393724971),
                              design3d.Point2D(-6.453654103266168, 10.412412821151062)],
                             [design3d.Point2D(2.0, 1.0), design3d.Point2D(0.0, 0.0)],
                             [design3d.Point2D(6.898979485566356, 11.898979485566356),
                              design3d.Point2D(-2.8989794855663558, 2.1010205144336442)]]]

        frame1 = design3d.Frame2D(design3d.O2D, design3d.Vector2D(0.7071067811865475, 0.7071067811865475),
                                 design3d.Vector2D(-0.7071067811865475, 0.7071067811865475))
        frame2 = design3d.OXY
        parabola1 = curves.Parabola2D(frame1, 1)
        parabola2 = curves.Parabola2D(frame2, 1)

        line1 = curves.Line2D(design3d.Point2D(5, 0), design3d.Point2D(-6, 10))
        line2 = curves.Line2D(design3d.Point2D(-10, -5), design3d.Point2D(10, 5))
        line3 = curves.Line2D(design3d.Point2D(-10, -5), design3d.Point2D(5, 10))
        ax = parabola1.plot()
        parabola1.frame.plot(ax)
        for i, hyperbola in enumerate([parabola1, parabola2]):
            for j, line in enumerate([line1, line2, line3]):
                line_intersections = hyperbola.line_intersections(line)
                for intersection, expected_result in zip(line_intersections, expected_results[i][j]):
                    self.assertTrue(intersection.is_close(expected_result))

    def test_point_belongs(self):
        parabola = curves.Parabola2D(design3d.OXY, 0.25)
        point1 = design3d.Point2D(0.9051724137931036, 0.8193370986920336)
        point2 = design3d.Point2D(0.2051724137931036, -0.8193370986920336)
        self.assertTrue(parabola.point_belongs(point1))
        self.assertFalse(parabola.point_belongs(point2))

    def test_tangent(self):
        parabola = curves.Parabola2D(design3d.OXY, 0.25)
        point1 = design3d.Point2D(0.9051724137931036, 0.8193370986920336)
        point2 = design3d.Point2D(-0.8189655172413792, 0.6707045184304398)
        tangent_vector1 = parabola.tangent(point1)
        tangent_vector2 = parabola.tangent(point2)
        self.assertTrue(tangent_vector1.is_close(design3d.Vector2D(1.0, 1.8103448275862073)))
        self.assertTrue(tangent_vector2.is_close(design3d.Vector2D(1.0, -1.6379310344827585)))


class TestParabola3D(unittest.TestCase):
    def test_line_intersections(self):
        expected_results = [[[design3d.Point3D(2.77966655993497, 0.8078693778774468, 0.8078693778774468),
                             design3d.Point3D(0.9512856633182674, -3.9353925603457114, -3.9353925603457114)],
                            [design3d.Point3D(-0.17313627385849073, -2.067615656403906, -2.067615656403906)],
                            []],
                            [[design3d.Point3D(2.5376884422110555, 1.6099656574328935, 0.0),
                             design3d.Point3D(-3.9949748743718594, 3.9899560617156133, 0.0)],
                            [design3d.Point3D(-2.487437185929648, 1.5468359384864017, 0.0)],
                            []]]
        vector1 = design3d.Vector3D(1, 1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        vector3 = vector1.cross(vector2)
        frame1 = design3d.Frame3D(design3d.O3D, vector1, vector2, vector3)
        frame2 = design3d.OXYZ
        parabola1 = curves.Parabola3D(frame1, 1)
        parabola2 = curves.Parabola3D(frame2, 1)
        for i, parabola in enumerate([parabola1, parabola2]):
            points = parabola.get_points(number_points=200)
            line3d_1 = curves.Line3D(points[20], points[150])
            line3d_3 = curves.Line3D(points[50], design3d.Point3D(1, 1.5, -1.5))
            line3d_4 = curves.Line3D(design3d.Point3D(-2., -1.5, 1.5), design3d.Point3D(1.0, 1.5, -1.5))
            for j, line in enumerate([line3d_1, line3d_3, line3d_4]):
                line_intersections = parabola.line_intersections(line)
                for intersection, expected_result in zip(line_intersections, expected_results[i][j]):
                    self.assertTrue(intersection.is_close(expected_result))

    def test_trim(self):
        parabola = curves.Parabola3D(design3d.Frame3D(
            design3d.Point3D(-0.43301270189243873, 0.0, 0.7500000000003803),
            design3d.Vector3D(-0.0, 1.0, 0.0), design3d.Vector3D(0.5000000000002298, 0.0, 0.8660254037843059),
            design3d.Vector3D(0.8660254037844387, 0.0, -0.49999999999999994)), 0.21650635094600354)
        point_start = design3d.Point3D(1.6339745962174324, -1.8921223583379627, 4.330127018924)
        point_end = design3d.Point3D(1.6339745962174324, 1.8921223583379627, 4.330127018924)
        bspline = parabola.trim(point_start, point_end)
        self.assertAlmostEqual(bspline.length(), 9.425679739766021, 5)

    def test_point_belongs(self):
        vector1 = design3d.Vector3D(1, 1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        vector3 = vector1.cross(vector2)
        frame = design3d.Frame3D(design3d.O3D, vector1, vector2, vector3)
        parabola3d = curves.Parabola3D(frame, 0.25)
        point1 = design3d.Point3D(0.34684705570366325, 0.16253460292661448, 0.16253460292661448)
        point2 = design3d.Point3D(0.3259646383580663, -1.0961993491191613, -1.0961993491191613)
        point3 = design3d.Point3D(2.3259646383580663, 1.0961993491191613, -3.0961993491191613)
        self.assertTrue(parabola3d.point_belongs(point1))
        self.assertTrue(parabola3d.point_belongs(point2))
        self.assertFalse(parabola3d.point_belongs(point3))

    def test_tangent(self):
        vector1 = design3d.Vector3D(1, 1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        vector3 = vector1.cross(vector2)
        frame = design3d.Frame3D(design3d.O3D, vector1, vector2, vector3)
        parabola3d = curves.Parabola3D(frame, 0.25)
        point1 = design3d.Point3D(0.34684705570366325, 0.16253460292661448, 0.16253460292661448)
        point2 = design3d.Point3D(0.3259646383580663, -1.0961993491191613, -1.0961993491191613)
        tangent_vector1 = parabola3d.tangent(point1)
        tangent_vector2 = parabola3d.tangent(point2)
        self.assertTrue(tangent_vector1.is_close(
            design3d.Vector3D(1.2108389957713368, 0.2606059058983855, 0.2606059058983855)))
        self.assertTrue(tangent_vector2.is_close(
            design3d.Vector3D(-1.1823406379820662, 1.4571957227751613, 1.4571957227751613)))


if __name__ == '__main__':
    unittest.main()
