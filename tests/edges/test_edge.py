import unittest
from geomdl import utilities

import design3d
from design3d import edges, curves
import design3d.step


class TestEdge(unittest.TestCase):

    arc = edges.Arc2D.from_3_points(design3d.Point2D(0, 0.3), design3d.Point2D(1, -0.3), design3d.Point2D(2, 2))
    u_vector = design3d.Vector2D(0.7071067811865475, 0.7071067811865475)
    v_vector = design3d.Vector2D(-0.7071067811865475, 0.7071067811865475)
    frame = design3d.Frame2D(design3d.O2D, u_vector, v_vector)
    ellipse2d = curves.Ellipse2D(2, 1, frame)
    lineseg = edges.LineSegment2D(design3d.Point2D(0, 0.2), design3d.Point2D(3, -0.2))
    arc_ellipse2d = edges.ArcEllipse2D(ellipse2d, start=design3d.Point2D(0.5, 1.5), end=design3d.Point2D(1.5, 0.5))

    DEGREE = 3
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 1), design3d.Point2D(2, -1), design3d.Point2D(3, 0)]
    knotvector = utilities.generate_knot_vector(DEGREE, len(points))
    knot_multiplicity = [1] * len(knotvector)
    bspline1 = edges.BSplineCurve2D(DEGREE, points, knot_multiplicity, knotvector, None)

    linesegment3d = edges.LineSegment3D(design3d.Point3D(1, 2, 4), design3d.Point3D(-1, 5, -3))

    vector1 = design3d.Vector3D(1, 1, 1)
    vector1 = vector1.unit_vector()
    vector2 = vector1.deterministic_unit_normal_vector()
    vector3 = vector1.cross(vector2)

    circle3d = curves.Circle3D(design3d.Frame3D(design3d.O3D, vector1, vector2, vector3), 1)
    arc3d = edges.Arc3D(
        circle3d,
        start=design3d.Point3D(0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
        end=design3d.Point3D(-0.9855985596534886, -0.11957315586905026, -0.11957315586905026),
    )

    ellipse3d = curves.Ellipse3D(2, 1, design3d.Frame3D(design3d.Point3D(1, 2, 1), vector3, vector1, vector2))
    arc_ellipse3d = edges.ArcEllipse3D(
        ellipse3d,
        start=design3d.Point3D(0.42264973081037405, 1.4226497308103743, 0.42264973081037427),
        end=design3d.Point3D(1.577350269189626, 2.5773502691896253, 1.5773502691896257),
    )

    def test_direction_independent_is_close(self):
        self.assertFalse(self.bspline1.direction_independent_is_close(self.arc))
        self.assertTrue(self.bspline1.direction_independent_is_close(self.bspline1))
        self.assertTrue(self.bspline1.direction_independent_is_close(self.bspline1.reverse()))
        self.assertTrue(self.lineseg.direction_independent_is_close(self.lineseg))
        self.assertTrue(self.lineseg.direction_independent_is_close(self.lineseg.reverse()))
        self.assertTrue(self.arc.direction_independent_is_close(self.arc))
        self.assertTrue(self.arc.direction_independent_is_close(self.arc.reverse()))
        self.assertFalse(self.arc.direction_independent_is_close(self.arc.complementary()))
        self.assertTrue(self.arc_ellipse2d.direction_independent_is_close(self.arc_ellipse2d))
        self.assertTrue(self.arc_ellipse2d.direction_independent_is_close(self.arc_ellipse2d.reverse()))
        self.assertFalse(self.arc_ellipse2d.direction_independent_is_close(self.arc_ellipse2d.complementary()))

    def test_trim(self):
        point1 = design3d.Point3D(0.1744332430903422, 0.033444245563080795, 0.07798520478978595)
        point2 = design3d.Point3D(0.177922447446, 0.03351981629780013, 0.07827867754649165)
        arc3d = edges.Arc3D.from_json("edges/arc3d_split_between_two_points.json")
        new_arc3d = arc3d.trim(point1, point2)
        self.assertTrue(new_arc3d)
        self.assertTrue(new_arc3d.start.is_close(point2))
        self.assertTrue(new_arc3d.end.is_close(point1))

    def test_from_step(self):
        step = design3d.step.Step.from_file(filepath="edges/test_edge_from_step.stp")
        model = step.to_volume_model()
        self.assertTrue(model.primitives[0].faces[0].outer_contour3d.is_ordered())

    def test_to_step(self):
        current_id = 1
        content, current_id = self.linesegment3d.to_step(current_id)
        self.assertIn("LINE", content)
        self.assertIn("EDGE_CURVE", content)
        content, current_id = self.arc3d.to_step(current_id)
        self.assertIn("CIRCLE", content)
        self.assertIn("EDGE_CURVE", content)
        content, current_id = self.arc_ellipse3d.to_step(current_id)
        self.assertIn("ELLIPSE", content)
        self.assertIn("EDGE_CURVE", content)


if __name__ == "__main__":
    unittest.main()
