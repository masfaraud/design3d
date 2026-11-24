"""Tests for design3d.primitives2d.RoundedRectangle2D."""

import math
import unittest

import design3d
from design3d import edges, wires
from design3d.primitives2d import RoundedRectangle2D


class TestRoundedRectangle2D(unittest.TestCase):
    def setUp(self):
        self.center = design3d.Point2D(0.3, -0.2)
        self.rectangle = RoundedRectangle2D(0.4, 0.2, 0.05, center=self.center, angle=0.3, name="rect")

    def test_geometry(self):
        self.assertTrue(self.rectangle.is_ordered())
        self.assertAlmostEqual(self.rectangle.area(), 0.4 * 0.2 - (4 - math.pi) * 0.05**2)
        self.assertAlmostEqual(self.rectangle.length(), 2 * (0.4 + 0.2) - 8 * 0.05 + 2 * math.pi * 0.05)
        self.assertTrue(self.rectangle.center_of_mass().is_close(self.center))
        self.assertEqual(len(self.rectangle.primitives), 8)

    def test_angle(self):
        rectangle = RoundedRectangle2D(0.4, 0.2, 0.05, angle=0.5 * math.pi)
        x_min, x_max, y_min, y_max = rectangle.bounding_rectangle.bounds()
        self.assertAlmostEqual(x_max - x_min, 0.2)
        self.assertAlmostEqual(y_max - y_min, 0.4)

    def test_sharp_corners(self):
        rectangle = RoundedRectangle2D(0.4, 0.2, 0.0)
        self.assertEqual(len(rectangle.primitives), 4)
        self.assertTrue(all(isinstance(primitive, edges.LineSegment2D) for primitive in rectangle.primitives))
        self.assertAlmostEqual(rectangle.area(), 0.08)

    def _assert_parameters(self, rectangle, center, angle):
        self.assertIsInstance(rectangle, RoundedRectangle2D)
        self.assertEqual((rectangle.width, rectangle.height, rectangle.corner_radius), (0.4, 0.2, 0.05))
        self.assertTrue(rectangle.center.is_close(center))
        self.assertAlmostEqual(rectangle.angle, angle)

    def test_copy(self):
        copied = self.rectangle.copy()
        self._assert_parameters(copied, self.center, 0.3)
        self.assertIsNot(copied.center, self.rectangle.center)
        self.assertTrue(copied.is_superposing(self.rectangle))

    def test_rotation(self):
        rotation_center = design3d.Point2D(1.0, 1.0)
        rotated = self.rectangle.rotation(rotation_center, 0.4)
        self._assert_parameters(rotated, self.center.rotation(rotation_center, 0.4), 0.7)
        expected = wires.Contour2D(self.rectangle.primitives).rotation(rotation_center, 0.4)
        self.assertTrue(rotated.is_superposing(expected))

    def test_translation(self):
        offset = design3d.Vector2D(0.1, 0.2)
        translated = self.rectangle.translation(offset)
        self._assert_parameters(translated, self.center + offset, 0.3)

    def test_frame_mapping(self):
        frame = design3d.Frame2D(design3d.Point2D(1.0, 2.0), design3d.Y2D, -design3d.X2D)
        mapped = self.rectangle.frame_mapping(frame, "new")
        self.assertIsInstance(mapped, RoundedRectangle2D)
        expected = wires.Contour2D(self.rectangle.primitives).frame_mapping(frame, "new")
        self.assertTrue(mapped.is_superposing(expected))

    def test_serialization(self):
        rectangle = RoundedRectangle2D.dict_to_object(self.rectangle.to_dict())
        self._assert_parameters(rectangle, self.center, 0.3)
        self.assertEqual(rectangle.name, "rect")

    def test_operations_returning_generic_contours(self):
        self.assertAlmostEqual(self.rectangle.invert().area(), self.rectangle.area())
        self.assertAlmostEqual(self.rectangle.offset(0.01).area(), 0.42 * 0.22 - (4 - math.pi) * 0.06**2)
        self.assertAlmostEqual(self.rectangle.offset(-0.01).area(), 0.38 * 0.18 - (4 - math.pi) * 0.04**2)
        self.assertAlmostEqual(self.rectangle.offset_lines([0], 0.01).area(), self.rectangle.area() + 0.4 * 0.01)
        line = design3d.curves.Line2D(design3d.O2D, design3d.Point2D(0.0, 1.0))
        self.assertAlmostEqual(self.rectangle.axial_symmetry(line).area(), self.rectangle.area())


if __name__ == "__main__":
    unittest.main()
