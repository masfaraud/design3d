"""Tests for design3d.primitives2d.RegularPolygon2D."""

import math
import unittest

import design3d
from design3d import wires
from design3d.primitives2d import RegularPolygon2D


class TestRegularPolygon2D(unittest.TestCase):
    def setUp(self):
        self.center = design3d.Point2D(0.3, -0.2)
        self.polygon = RegularPolygon2D(6, 0.1, center=self.center, angle=0.3, name="hexagon")

    def test_geometry(self):
        self.assertEqual(len(self.polygon.points), 6)
        self.assertTrue(self.polygon.is_ordered())
        self.assertAlmostEqual(self.polygon.area(), 3 * 0.1**2 * math.sin(math.pi / 3))
        self.assertAlmostEqual(self.polygon.length(), 6 * 0.1)
        self.assertTrue(self.polygon.center_of_mass().is_close(self.center))

    def test_angle(self):
        expected = self.center + 0.1 * design3d.Vector2D(math.cos(0.3), math.sin(0.3))
        self.assertTrue(self.polygon.points[0].is_close(expected))

    def _assert_parameters(self, polygon, center, angle):
        self.assertIsInstance(polygon, RegularPolygon2D)
        self.assertEqual((polygon.number_sides, polygon.radius), (6, 0.1))
        self.assertTrue(polygon.center.is_close(center))
        self.assertAlmostEqual(polygon.angle, angle)

    def test_copy(self):
        copied = self.polygon.copy()
        self._assert_parameters(copied, self.center, 0.3)
        self.assertIsNot(copied.center, self.polygon.center)
        self.assertEqual(copied, self.polygon)

    def test_rotation(self):
        rotation_center = design3d.Point2D(1.0, 1.0)
        rotated = self.polygon.rotation(rotation_center, 0.4)
        self._assert_parameters(rotated, self.center.rotation(rotation_center, 0.4), 0.7)
        expected = wires.ClosedPolygon2D(self.polygon.points).rotation(rotation_center, 0.4)
        self.assertTrue(rotated.is_superposing(expected))

    def test_translation(self):
        offset = design3d.Vector2D(0.1, 0.2)
        translated = self.polygon.translation(offset)
        self._assert_parameters(translated, self.center + offset, 0.3)

    def test_frame_mapping(self):
        frame = design3d.Frame2D(design3d.Point2D(1.0, 2.0), design3d.Y2D, -design3d.X2D)
        mapped = self.polygon.frame_mapping(frame, "new")
        self.assertIsInstance(mapped, RegularPolygon2D)
        expected = wires.ClosedPolygon2D(self.polygon.points).frame_mapping(frame, "new")
        self.assertTrue(mapped.is_superposing(expected))

    def test_serialization(self):
        polygon = RegularPolygon2D.dict_to_object(self.polygon.to_dict())
        self._assert_parameters(polygon, self.center, 0.3)
        self.assertEqual(polygon.name, "hexagon")

    def test_operations_returning_generic_contours(self):
        self.assertAlmostEqual(self.polygon.invert().area(), self.polygon.area())
        self.assertGreater(self.polygon.offset(0.01).area(), self.polygon.area())
        line = design3d.curves.Line2D(design3d.O2D, design3d.Point2D(0.0, 1.0))
        self.assertAlmostEqual(self.polygon.axial_symmetry(line).area(), self.polygon.area())
        self.assertIs(self.polygon.simplify().__class__, wires.ClosedPolygon2D)


if __name__ == "__main__":
    unittest.main()
