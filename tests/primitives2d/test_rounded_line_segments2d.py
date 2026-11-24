"""Tests for design3d.primitives2d rounded line segments."""

import unittest

import design3d
from design3d import wires
from design3d.primitives2d import ClosedRoundedLineSegments2D, OpenedRoundedLineSegments2D


class TestClosedRoundedLineSegments2D(unittest.TestCase):
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(1, 1), design3d.Point2D(0, 1)]
    contour = ClosedRoundedLineSegments2D(points, {0: 0.1, 2: 0.2}, name="contour")

    def test_invert(self):
        inverted = self.contour.invert()
        self.assertIsInstance(inverted, ClosedRoundedLineSegments2D)
        self.assertEqual(inverted.points, self.points[::-1])
        self.assertEqual(inverted.radius, {3: 0.1, 1: 0.2})
        self.assertTrue(inverted.is_superposing(wires.Contour2D(self.contour.primitives).invert()))
        self.assertAlmostEqual(inverted.area(), self.contour.area())


class TestOpenedRoundedLineSegments2D(unittest.TestCase):
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(1, 1), design3d.Point2D(2, 1)]
    wire = OpenedRoundedLineSegments2D(points, {1: 0.1, 2: 0.2}, name="wire")

    def test_invert(self):
        inverted = self.wire.invert()
        self.assertIsInstance(inverted, OpenedRoundedLineSegments2D)
        self.assertEqual(inverted.points, self.points[::-1])
        self.assertEqual(inverted.radius, {2: 0.1, 1: 0.2})
        self.assertTrue(inverted.primitives[0].start.is_close(self.wire.primitives[-1].end))
        self.assertTrue(inverted.primitives[-1].end.is_close(self.wire.primitives[0].start))
        self.assertAlmostEqual(inverted.length(), self.wire.length())


if __name__ == "__main__":
    unittest.main()
