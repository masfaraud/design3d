import unittest
from itertools import product

from geomdl import utilities

import design3d
from design3d import edges, curves

class TestEdge2DIntersections(unittest.TestCase):

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

    def test_edge_intersections(self):
        expected_results = [[design3d.Point2D(0.2154767869546837, 0.17126976173937553),
                             design3d.Point2D(1.5, 0.0),
                             design3d.Point2D(2.7845232130453157, -0.17126976173937541)],
                            [design3d.Point2D(0.13933368620308095, 0.12052092182572971),
                             design3d.Point2D(1.7686123664971742, -0.12999927610320117)],
                            [design3d.Point2D(1.3169500371767962, 0.0901619768300107)],
                            [design3d.Point2D(0.2154767869546837, 0.17126976173937553),
                             design3d.Point2D(1.5, 0.0),
                             design3d.Point2D(2.7845232130453157, -0.17126976173937541)],
                            [design3d.Point2D(1.8893801268948387, -0.05191735025264532),
                             design3d.Point2D(0.07997689764965754, 0.18933641364671217)],
                            [design3d.Point2D(1.2821273688601553, 0.029049684151979283)],
                            [design3d.Point2D(0.13933368620308095, 0.12052092182572971),
                             design3d.Point2D(1.7686123664971742, -0.12999927610320117)],
                            [design3d.Point2D(1.8893801268948387, -0.05191735025264532),
                             design3d.Point2D(0.07997689764965754, 0.18933641364671217)],
                            [design3d.Point2D(1.059165466205527, -0.3036640978242126)],
                            [design3d.Point2D(1.3169500371767962, 0.0901619768300107)],
                            [design3d.Point2D(1.2821273688601553, 0.029049684151979283)],
                            [design3d.Point2D(1.059165466205527, -0.3036640978242126)]]

        intersection_results = []
        for edge1, edge2 in product([self.bspline1, self.lineseg, self.arc, self.arc_ellipse2d], repeat=2):
            if edge1 == edge2:
                continue
            intersections = edge1.intersections(edge2)
            intersection_results.append(intersections)
        for intersections, expected_intersections in zip(intersection_results, expected_results):
            for intersection, expected_intersection in zip(intersections, expected_intersections):
                self.assertTrue(intersection.is_close(expected_intersection))


if __name__ == '__main__':
    unittest.main()
