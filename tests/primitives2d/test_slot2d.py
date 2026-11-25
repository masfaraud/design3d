"""Tests for design3d.primitives2d.Slot2D."""

import math
import unittest

import design3d
from design3d import edges, wires
from design3d.primitives2d import Slot2D


class TestSlot2D(unittest.TestCase):
    def setUp(self):
        self.center = design3d.Point2D(0.3, -0.2)
        self.slot = Slot2D(0.5, 0.1, center=self.center, angle=0.3, name="slot")

    def test_geometry(self):
        self.assertTrue(self.slot.is_ordered())
        self.assertEqual(
            [primitive.__class__ for primitive in self.slot.primitives], [edges.LineSegment2D, edges.Arc2D] * 2
        )
        self.assertAlmostEqual(self.slot.area(), 0.4 * 0.1 + math.pi * 0.05**2)
        self.assertAlmostEqual(self.slot.length(), 2 * 0.4 + math.pi * 0.1)
        self.assertTrue(self.slot.center_of_mass().is_close(self.center))

    def test_bounding_rectangle(self):
        # The arcs of the slot reach x = -0.25 and x = 0.25: the bounding rectangle and point_inside must be exact
        slot = Slot2D(0.5, 0.1)
        for value, expected_value in zip(slot.bounding_rectangle.bounds(), (-0.25, 0.25, -0.05, 0.05)):
            self.assertAlmostEqual(value, expected_value, places=12)
        x_min, y_min = slot.bounding_points()[0]
        x_max, y_max = slot.bounding_points()[1]
        for value, expected_value in zip((x_min, x_max, y_min, y_max), (-0.25, 0.25, -0.05, 0.05)):
            self.assertAlmostEqual(value, expected_value, places=12)
        for point in (design3d.Point2D(-0.25, 0.0), design3d.Point2D(0.25, 0.0)):
            self.assertTrue(slot.point_inside(point, include_edge_points=True))
            self.assertFalse(slot.point_inside(point, include_edge_points=False))

    def test_angle(self):
        slot = Slot2D(0.5, 0.1, angle=0.5 * math.pi)
        self.assertTrue(slot.primitives[1].middle_point().is_close(design3d.Point2D(0.0, 0.25)))
        self.assertTrue(slot.primitives[3].middle_point().is_close(design3d.Point2D(0.0, -0.25)))

    def _assert_parameters(self, slot, center, angle):
        self.assertIsInstance(slot, Slot2D)
        self.assertEqual((slot.total_length, slot.width), (0.5, 0.1))
        self.assertTrue(slot.center.is_close(center))
        self.assertAlmostEqual(slot.angle, angle)

    def test_copy(self):
        copied = self.slot.copy()
        self._assert_parameters(copied, self.center, 0.3)
        self.assertIsNot(copied.center, self.slot.center)
        self.assertTrue(copied.is_superposing(self.slot))

    def test_rotation(self):
        rotation_center = design3d.Point2D(1.0, 1.0)
        rotated = self.slot.rotation(rotation_center, 0.4)
        self._assert_parameters(rotated, self.center.rotation(rotation_center, 0.4), 0.7)
        expected = wires.Contour2D(self.slot.primitives).rotation(rotation_center, 0.4)
        self.assertTrue(rotated.is_superposing(expected))

    def test_translation(self):
        offset = design3d.Vector2D(0.1, 0.2)
        translated = self.slot.translation(offset)
        self._assert_parameters(translated, self.center + offset, 0.3)

    def test_frame_mapping(self):
        frame = design3d.Frame2D(design3d.Point2D(1.0, 2.0), design3d.Y2D, -design3d.X2D)
        mapped = self.slot.frame_mapping(frame, "new")
        self.assertIsInstance(mapped, Slot2D)
        expected = wires.Contour2D(self.slot.primitives).frame_mapping(frame, "new")
        self.assertTrue(mapped.is_superposing(expected))

    def test_serialization(self):
        slot = Slot2D.dict_to_object(self.slot.to_dict())
        self._assert_parameters(slot, self.center, 0.3)
        self.assertEqual(slot.name, "slot")

    def test_operations_returning_generic_contours(self):
        self.assertAlmostEqual(self.slot.invert().area(), self.slot.area())
        line = design3d.curves.Line2D(design3d.O2D, design3d.Point2D(0.0, 1.0))
        self.assertAlmostEqual(self.slot.axial_symmetry(line).area(), self.slot.area())


if __name__ == "__main__":
    unittest.main()
