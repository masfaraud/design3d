"""Tests for design3d.primitives2d.CirclesConvexHull2D."""

import math
import unittest

import design3d
from design3d import edges, wires
from design3d.primitives2d import CirclesConvexHull2D, Slot2D


def two_circles_hull_area(radius1, radius2, distance):
    """Area of the convex hull of two circles: two sectors and two right trapezoids along the tangents."""
    alpha = math.asin((radius1 - radius2) / distance)
    tangent_length = distance * math.cos(alpha)
    return (
        0.5 * (math.pi + 2 * alpha) * radius1**2
        + 0.5 * (math.pi - 2 * alpha) * radius2**2
        + (radius1 + radius2) * tangent_length
    )


class TestCirclesConvexHull2D(unittest.TestCase):
    def setUp(self):
        # Crank web like profile: a large circle and a smaller one
        self.centers = [design3d.Point2D(0.1, 0.2), design3d.Point2D(0.1, 0.25)]
        self.radii = [0.06, 0.025]
        self.hull = CirclesConvexHull2D(self.centers, self.radii, name="web")

    def test_two_circles(self):
        self.assertTrue(self.hull.is_ordered())
        self.assertEqual(
            sorted(primitive.__class__.__name__ for primitive in self.hull.primitives),
            ["Arc2D", "Arc2D", "LineSegment2D", "LineSegment2D"],
        )
        self.assertTrue(self.hull.edge_polygon.is_trigo)
        self.assertAlmostEqual(self.hull.area(), two_circles_hull_area(0.06, 0.025, 0.05))
        alpha = math.asin((0.06 - 0.025) / 0.05)
        expected_length = (math.pi + 2 * alpha) * 0.06 + (math.pi - 2 * alpha) * 0.025 + 2 * 0.05 * math.cos(alpha)
        self.assertAlmostEqual(self.hull.length(), expected_length)

    def test_equal_circles_is_a_slot(self):
        hull = CirclesConvexHull2D([design3d.Point2D(-0.2, 0.0), design3d.Point2D(0.2, 0.0)], [0.05, 0.05])
        self.assertTrue(hull.is_superposing(Slot2D(0.5, 0.1)))

    def test_three_circles(self):
        centers = [design3d.Point2D(0.0, 0.0), design3d.Point2D(0.3, 0.0), design3d.Point2D(0.1, 0.25)]
        radii = [0.05, 0.08, 0.03]
        hull = CirclesConvexHull2D(centers, radii)
        self.assertTrue(hull.is_ordered())
        self.assertTrue(hull.edge_polygon.is_trigo)
        self.assertEqual(len(hull.primitives), 6)
        # The hull encloses all the circles (points slightly inside them, as the bounding rectangle of contours
        # with arcs is computed on discretization points) and the tangents do not cut any circle
        for center, radius in zip(centers, radii):
            for i in range(12):
                angle = 2 * math.pi * i / 12
                point = center + 0.99 * radius * design3d.Vector2D(math.cos(angle), math.sin(angle))
                self.assertTrue(hull.point_inside(point))
        for primitive in hull.primitives:
            if isinstance(primitive, edges.LineSegment2D):
                for center, radius in zip(centers, radii):
                    self.assertGreaterEqual(primitive.line.point_distance(center), radius - 1e-9)

    def test_contained_circle_is_ignored(self):
        centers = [*self.centers, design3d.Point2D(0.11, 0.2)]
        hull = CirclesConvexHull2D(centers, [*self.radii, 0.02])
        self.assertEqual(len(hull.primitives), 4)
        self.assertAlmostEqual(hull.area(), self.hull.area())

    def test_aligned_circles(self):
        # The middle circle touches the two tangents: it adds no edge
        centers = [design3d.Point2D(-0.2, 0.0), design3d.Point2D(0.0, 0.0), design3d.Point2D(0.2, 0.0)]
        vertical_centers = [center.rotation(design3d.O2D, 0.5 * math.pi) for center in centers]
        for aligned_centers in (centers, vertical_centers):
            for order in ([0, 1, 2], [1, 0, 2], [1, 2, 0]):
                hull = CirclesConvexHull2D([aligned_centers[i] for i in order], [0.05, 0.05, 0.05])
                self.assertTrue(hull.is_ordered())
                self.assertEqual(len(hull.primitives), 4)
                self.assertAlmostEqual(hull.area(), 0.4 * 0.1 + math.pi * 0.05**2)

    def test_single_circle(self):
        hull = CirclesConvexHull2D([design3d.Point2D(0.1, 0.0)], [0.05])
        self.assertAlmostEqual(hull.area(), math.pi * 0.05**2)
        self.assertTrue(hull.is_ordered())

    def test_offset(self):
        offset_hull = self.hull.offset(0.01)
        self.assertIsInstance(offset_hull, CirclesConvexHull2D)
        for radius, expected in zip(offset_hull.radii, [0.07, 0.035]):
            self.assertAlmostEqual(radius, expected)
        self.assertAlmostEqual(offset_hull.area(), two_circles_hull_area(0.07, 0.035, 0.05))
        inner_hull = self.hull.offset(-0.01)
        self.assertIsInstance(inner_hull, CirclesConvexHull2D)
        self.assertAlmostEqual(inner_hull.area(), two_circles_hull_area(0.05, 0.015, 0.05))
        # A circle of the hull would vanish
        with self.assertRaises(ValueError):
            self.hull.offset(-0.03)

    def _assert_parameters(self, hull, centers):
        self.assertIsInstance(hull, CirclesConvexHull2D)
        self.assertEqual(len(hull.radii), len(self.radii))
        for radius, expected in zip(hull.radii, self.radii):
            self.assertAlmostEqual(radius, expected)
        for center, expected in zip(hull.centers, centers):
            self.assertTrue(center.is_close(expected))

    def test_copy(self):
        copied = self.hull.copy()
        self._assert_parameters(copied, self.centers)
        self.assertIsNot(copied.centers[0], self.hull.centers[0])
        self.assertTrue(copied.is_superposing(self.hull))

    def test_rotation(self):
        rotation_center = design3d.Point2D(1.0, 1.0)
        rotated = self.hull.rotation(rotation_center, 0.4)
        self._assert_parameters(rotated, [center.rotation(rotation_center, 0.4) for center in self.centers])
        expected = wires.Contour2D(self.hull.primitives).rotation(rotation_center, 0.4)
        self.assertTrue(rotated.is_superposing(expected))

    def test_translation(self):
        offset = design3d.Vector2D(0.1, 0.2)
        translated = self.hull.translation(offset)
        self._assert_parameters(translated, [center + offset for center in self.centers])

    def test_frame_mapping(self):
        # Indirect frame: the profile is rebuilt counterclockwise
        frame = design3d.Frame2D(design3d.Point2D(1.0, 2.0), design3d.Y2D, design3d.X2D)
        mapped = self.hull.frame_mapping(frame, "new")
        self.assertIsInstance(mapped, CirclesConvexHull2D)
        self.assertTrue(mapped.edge_polygon.is_trigo)
        expected = wires.Contour2D(self.hull.primitives).frame_mapping(frame, "new")
        self.assertTrue(mapped.is_superposing(expected))

    def test_serialization(self):
        hull = CirclesConvexHull2D.dict_to_object(self.hull.to_dict())
        self._assert_parameters(hull, self.centers)
        self.assertEqual(hull.name, "web")

    def test_operations_returning_generic_contours(self):
        self.assertAlmostEqual(self.hull.invert().area(), self.hull.area())
        line = design3d.curves.Line2D(design3d.O2D, design3d.Point2D(0.0, 1.0))
        self.assertAlmostEqual(self.hull.axial_symmetry(line).area(), self.hull.area())

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            CirclesConvexHull2D([], [])
        with self.assertRaises(ValueError):
            CirclesConvexHull2D([design3d.O2D], [0.1, 0.2])
        with self.assertRaises(ValueError):
            CirclesConvexHull2D([design3d.O2D], [0.0])


if __name__ == "__main__":
    unittest.main()
