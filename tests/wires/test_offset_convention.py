"""
Consistency of the offset convention between the 2D wire and contour classes.

A positive offset moves the wire to the right of its direction of travel: it enlarges a counterclockwise (trigo)
contour and shrinks a clockwise one.
"""

import unittest

import design3d
from design3d import wires

OFFSET = 0.1
SQUARE = [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(1, 1), design3d.Point2D(0, 1)]


class TestClosedContoursOffset(unittest.TestCase):
    def test_closed_polygon2d(self):
        self.assertAlmostEqual(wires.ClosedPolygon2D(SQUARE).offset(OFFSET).area(), (1 + 2 * OFFSET) ** 2)
        self.assertAlmostEqual(wires.ClosedPolygon2D(SQUARE[::-1]).offset(OFFSET).area(), (1 - 2 * OFFSET) ** 2)

    def test_closed_polygon2d_non_square_angles(self):
        polygon = wires.ClosedPolygon2D([design3d.Point2D(0, 0), design3d.Point2D(2, 0), design3d.Point2D(0, 1)])
        offset_polygon = polygon.offset(OFFSET)
        # Each side of the offset triangle is at the offset distance from the original side.
        for side, offset_side in zip(polygon.line_segments, offset_polygon.line_segments):
            line = design3d.curves.Line2D(side.start, side.end)
            self.assertAlmostEqual(line.point_distance(offset_side.start), OFFSET)
            self.assertAlmostEqual(line.point_distance(offset_side.end), OFFSET)


if __name__ == "__main__":
    unittest.main()
