"""
Consistency of the offset convention between the 2D wire and contour classes.

A positive offset moves the wire to the right of its direction of travel: it enlarges a counterclockwise (trigo)
contour and shrinks a clockwise one.
"""

import math
import unittest

import design3d
from design3d import wires
from design3d.primitives2d import (
    ClosedRoundedLineSegments2D,
    OpenedRoundedLineSegments2D,
    RegularPolygon2D,
    RoundedRectangle2D,
    Slot2D,
)

OFFSET = 0.1
SQUARE = [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(1, 1), design3d.Point2D(0, 1)]
RADIUS = 0.2


def rounded_square_area(side, radius):
    return side**2 - (4 - math.pi) * radius**2


class TestClosedContoursOffset(unittest.TestCase):
    def _check(self, contour, expected_area_trigo, expected_area_clockwise):
        """Checks the offset of a contour given counterclockwise, and of the same contour inverted."""
        self.assertAlmostEqual(contour.offset(OFFSET).area(), expected_area_trigo)
        clockwise_contour = contour.__class__(SQUARE[::-1], *self._extra_args(contour))
        self.assertAlmostEqual(clockwise_contour.offset(OFFSET).area(), expected_area_clockwise)

    @staticmethod
    def _extra_args(contour):
        if isinstance(contour, ClosedRoundedLineSegments2D):
            return ({i: RADIUS for i in range(4)},)
        return ()

    def test_contour2d(self):
        self.assertAlmostEqual(wires.Contour2D.from_points(SQUARE).offset(OFFSET).area(), (1 + 2 * OFFSET) ** 2)
        self.assertAlmostEqual(wires.Contour2D.from_points(SQUARE[::-1]).offset(OFFSET).area(), (1 - 2 * OFFSET) ** 2)

    def test_closed_polygon2d(self):
        self._check(wires.ClosedPolygon2D(SQUARE), (1 + 2 * OFFSET) ** 2, (1 - 2 * OFFSET) ** 2)

    def test_closed_polygon2d_non_square_angles(self):
        polygon = wires.ClosedPolygon2D([design3d.Point2D(0, 0), design3d.Point2D(2, 0), design3d.Point2D(0, 1)])
        offset_polygon = polygon.offset(OFFSET)
        # Each side of the offset triangle is at the offset distance from the original side.
        for side, offset_side in zip(polygon.line_segments, offset_polygon.line_segments):
            line = design3d.curves.Line2D(side.start, side.end)
            self.assertAlmostEqual(line.point_distance(offset_side.start), OFFSET)
            self.assertAlmostEqual(line.point_distance(offset_side.end), OFFSET)

    def test_closed_rounded_line_segments2d(self):
        contour = ClosedRoundedLineSegments2D(SQUARE, {i: RADIUS for i in range(4)})
        self._check(
            contour,
            rounded_square_area(1 + 2 * OFFSET, RADIUS + OFFSET),
            rounded_square_area(1 - 2 * OFFSET, RADIUS - OFFSET),
        )

    def test_rounded_rectangle2d(self):
        rectangle = RoundedRectangle2D(1.0, 0.5, RADIUS)
        self.assertAlmostEqual(
            rectangle.offset(OFFSET).area(),
            (1 + 2 * OFFSET) * (0.5 + 2 * OFFSET) - (4 - math.pi) * (RADIUS + OFFSET) ** 2,
        )

    def test_regular_polygon2d(self):
        polygon = RegularPolygon2D(6, 1.0)
        apothem = math.cos(math.pi / 6) + OFFSET
        self.assertAlmostEqual(polygon.offset(OFFSET).area(), 6 * apothem**2 * math.tan(math.pi / 6))

    def test_slot2d(self):
        slot = Slot2D(1.0, 0.2)
        self.assertIsInstance(slot.offset(OFFSET), Slot2D)
        width = 0.2 + 2 * OFFSET
        self.assertAlmostEqual(slot.offset(OFFSET).area(), (1.0 - 0.2) * width + math.pi * width**2 / 4)


class TestOpenWiresOffset(unittest.TestCase):
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(2, 0.5)]

    def test_wire2d(self):
        offset_wire = wires.Wire2D.from_points(self.points).offset(OFFSET)
        # Traveling along +x, the right side is towards -y.
        self.assertAlmostEqual(offset_wire.primitives[0].start.y, -OFFSET)

    def test_opened_rounded_line_segments2d(self):
        offset_wire = OpenedRoundedLineSegments2D(self.points, {1: RADIUS}).offset(OFFSET)
        self.assertTrue(offset_wire.points[0].is_close(design3d.Point2D(0, -OFFSET)))

    def test_opened_rounded_line_segments2d_offset_lines(self):
        points = [
            design3d.Point2D(-1, 1),
            design3d.Point2D(0, 0),
            design3d.Point2D(1, 0),
            design3d.Point2D(2, 0),
            design3d.Point2D(3, 1),
        ]
        offset_wire = OpenedRoundedLineSegments2D(points, {}).offset_lines([1, 2], OFFSET)
        for index in (1, 2, 3):
            self.assertAlmostEqual(offset_wire.points[index].y, -OFFSET)


if __name__ == "__main__":
    unittest.main()
