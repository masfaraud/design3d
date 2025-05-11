import unittest
from itertools import product

from geomdl import utilities
import design3d
from design3d import curves
import design3d.edges as d3de
# import design3d.models.edges as edges_models

lineseg = d3de.LineSegment2D(design3d.Point2D(0, 0.2), design3d.Point2D(3, -0.2))

DEGREE = 3
points = [design3d.Point2D(0, 0), design3d.Point2D(1, 1), design3d.Point2D(2, -1), design3d.Point2D(3, 0)]
knotvector = utilities.generate_knot_vector(DEGREE, len(points))
knot_multiplicity = [1] * len(knotvector)
bspline1 = d3de.BSplineCurve2D(DEGREE, points, knot_multiplicity, knotvector, None)

arc = d3de.Arc2D.from_3_points(design3d.Point2D(0, 0.3), design3d.Point2D(1, -0.3), design3d.Point2D(2, 2))
u_vector = design3d.Vector2D(0.7071067811865475, 0.7071067811865475)
v_vector = design3d.Vector2D(-0.7071067811865475, 0.7071067811865475)
frame = design3d.Frame2D(design3d.O2D, u_vector, v_vector)
ellipse2d = curves.Ellipse2D(2, 1, frame)
arc_ellipse2d = d3de.ArcEllipse2D(ellipse2d, start=design3d.Point2D(0.5, 1.5), end=design3d.Point2D(1.5, 0.5))

vector1 = design3d.Vector3D(1, 1, 1)
vector1 = vector1.unit_vector()
vector2 = vector1.deterministic_unit_normal_vector()
vector3 = vector1.cross(vector2)

circle3d = curves.Circle3D(design3d.Frame3D(design3d.O3D, vector1, vector2, vector3), 1)
arc3d = d3de.Arc3D(circle3d, start=design3d.Point3D(0.5773502691896258, 0.5773502691896258, 0.5773502691896258),
                       end=design3d.Point3D(-0.9855985596534886, -0.11957315586905026, -0.11957315586905026))

linesegment3d = d3de.LineSegment3D(design3d.Point3D(1, 2, 4), design3d.Point3D(-1, 5, -3))

ellipse3d = curves.Ellipse3D(2, 1, design3d.Frame3D(design3d.Point3D(1, 2, 1), vector3, vector1, vector2))
arc_ellipse3d = d3de.ArcEllipse3D(ellipse3d,start=design3d.Point3D(0.42264973081037405, 1.4226497308103743, 0.42264973081037427),
                        end=design3d.Point3D(1.577350269189626, 2.5773502691896253, 1.5773502691896257))

def bspline_curve3d():
    """Bspline curve3d model."""
    degree = 5
    control_points = [design3d.Point3D(0, 3, 0),
                      design3d.Point3D(3, 2, 1),
                      design3d.Point3D(5, -1, 4),
                      design3d.Point3D(5, -4, 0),
                      design3d.Point3D(-1, -2, -3),
                      design3d.Point3D(-3, 4, 1)]
    knots = [0.0, 1.0]
    knot_multiplicities = [6, 6]
    weights = None  # [1, 2, 1, 2, 1, 2]
    return d3de.BSplineCurve3D(degree=degree, control_points=control_points,
                                knot_multiplicities=knot_multiplicities,
                                knots=knots,
                                weights=weights,
                                name='B Spline Curve 3D 1')

class TestEdgesDistances(unittest.TestCase):



    def test_edges_distances_2d(self):
        expected_distances = [3.0, 3.171929282184431, 1.413379747337626, 2.9154759474226504, 3.144603017460846,
                              3.2934193036985913, 1.4282856857085704, 2.8735269769962803, 3.183195634502654,
                              3.3500730304603152, 1.4456832294800965, 2.8575751838382266, 1.0000000009680357,
                              1.2027923774744735, 0.0, 1.2597969896641665]

        vector1 = design3d.Vector2D(1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        distances = []
        for edge1, edge2 in product([bspline1, lineseg,
                                     arc, arc_ellipse2d], repeat=2):
            edge2 = edge2.frame_mapping(design3d.Frame2D(design3d.Point2D(3, 3), vector1, vector2), 'new')
            dist, min_dist_point_arc, min_dist_point_lineseg = edge1.minimum_distance(edge2, True)
            distances.append(dist)
        for distance, expected_distance in zip(distances, expected_distances):
            self.assertAlmostEqual(distance, expected_distance)

    def test_edges_distances_3d(self):
        expected_distances = [3.297515976380515, 0.6600032792406747, 0.01931857722664732, 0.6383061365421937,
                              0.6600032792406747, 6.117055924652082, 2.6674164255110373, 1.2247448713912275,
                              0.019318579007616275, 2.6674164255110373, 5.084297068558137, 0.8731527317517747,
                              0.6383061445002628, 1.2247448713912275, 0.8731527317517747, 4.289502509060332]
        vector1 = design3d.Vector3D(1, 1, 1)
        vector1 = vector1.unit_vector()
        vector2 = vector1.deterministic_unit_normal_vector()
        vector3 = vector1.cross(vector2)

        distances = []
        for edge1, edge2 in product([bspline_curve3d(), linesegment3d,
                                     arc3d, arc_ellipse3d], repeat=2):
            if edge1 == edge2:
                edge2 = edge2.frame_mapping(design3d.Frame3D(design3d.Point3D(2, 5, -3), vector1, vector2, vector3),
                                            'new')
            dist, min_dist_point_arc, min_dist_point_lineseg = edge1.minimum_distance(edge2, True)
            distances.append(dist)
        for distance, expected_distance in zip(distances, expected_distances):
            self.assertAlmostEqual(distance, expected_distance)


if __name__ == '__main__':
    unittest.main()
