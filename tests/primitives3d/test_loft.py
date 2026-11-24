import math
import unittest

from scipy.spatial import ConvexHull

import design3d
from design3d import curves, faces, shells, wires
from design3d.base import deserialize
from design3d.primitives3d import Loft, loft_faces


def square(side: float) -> wires.Contour2D:
    """Square contour centered on the origin."""
    half = 0.5 * side
    return wires.ClosedPolygon2D(
        [
            design3d.Point2D(-half, -half),
            design3d.Point2D(half, -half),
            design3d.Point2D(half, half),
            design3d.Point2D(-half, half),
        ]
    )


def circle(radius: float) -> wires.Contour2D:
    """Circle contour centered on the origin."""
    return wires.Contour2D.from_circle(curves.Circle2D(design3d.OXY, radius))


def frame_at_height(height: float) -> design3d.Frame3D:
    return design3d.Frame3D(design3d.Point3D(0.0, 0.0, height), design3d.X3D, design3d.Y3D, design3d.Z3D)


class TestLoft(unittest.TestCase):
    def test_two_identical_squares_is_a_prism(self):
        loft = Loft([square(1.0), square(1.0)], [frame_at_height(0.0), frame_at_height(2.0)])
        # 4 lateral faces (one per side of the square) and 2 end caps.
        self.assertEqual(len(loft.faces), 6)
        self.assertEqual(sum(isinstance(face, faces.BSplineFace3D) for face in loft.faces), 4)
        self.assertEqual(sum(isinstance(face, faces.PlaneFace3D) for face in loft.faces), 2)
        self.assertAlmostEqual(loft.volume(), 2.0, places=6)

    def test_square_pyramid_frustum_with_three_sections(self):
        # Sections sizes vary linearly with height: the loft is exactly a pyramid frustum, also with a
        # degree 2 interpolation through the three sections.
        loft = Loft(
            [square(2.0), square(1.5), square(1.0)],
            [frame_at_height(0.0), frame_at_height(0.5), frame_at_height(1.0)],
        )
        area1, area2, height = 4.0, 1.0, 1.0
        expected_volume = height / 3 * (area1 + math.sqrt(area1 * area2) + area2)
        self.assertAlmostEqual(loft.volume(), expected_volume, places=6)
        # The middle section is interpolated
        self.assertTrue(loft.point_inside(design3d.Point3D(0.74, 0.74, 0.5)))
        self.assertFalse(loft.point_inside(design3d.Point3D(0.76, 0.76, 0.5)))

    def test_circular_frustum(self):
        radius1, radius2, height = 0.5, 0.25, 1.0
        loft = Loft([circle(radius1), circle(radius2)], [frame_at_height(0.0), frame_at_height(height)])
        expected_volume = math.pi * height / 3 * (radius1**2 + radius1 * radius2 + radius2**2)
        # Closed primitives give two faces each, to avoid periodic faces
        self.assertEqual(len(loft.faces), 4)
        # The volume is computed on the mesh, that discretizes the circles
        self.assertAlmostEqual(loft.volume(), expected_volume, delta=0.02 * expected_volume)

    def test_sections_in_tilted_frames(self):
        # Sections need not be parallel: the second one is rotated around the Y axis, through its center. All the
        # faces are planar, so the loft is the convex hull of the corners of the two sections.
        tilted_frame = frame_at_height(1.0).rotation(design3d.Point3D(0.0, 0.0, 1.0), design3d.Y3D, math.radians(20))
        loft = Loft([square(0.5), square(0.5)], [frame_at_height(0.0), tilted_frame])
        self.assertEqual(len(loft.faces), 6)
        corners = [
            [*point.to_3d(frame.origin, frame.u, frame.v)]
            for frame in (frame_at_height(0.0), tilted_frame)
            for point in square(0.5).points
        ]
        self.assertAlmostEqual(loft.volume(), ConvexHull(corners).volume, places=6)

    def test_incompatible_sections(self):
        triangle = wires.ClosedPolygon2D(
            [design3d.Point2D(0.0, 0.0), design3d.Point2D(1.0, 0.0), design3d.Point2D(0.0, 1.0)]
        )
        with self.assertRaises(ValueError):
            Loft([square(1.0), triangle], [frame_at_height(0.0), frame_at_height(1.0)])

    def test_wrong_number_of_frames(self):
        with self.assertRaises(ValueError):
            Loft([square(1.0), square(1.0)], [frame_at_height(0.0)])

    def test_single_section(self):
        with self.assertRaises(ValueError):
            Loft([square(1.0)], [frame_at_height(0.0)])

    def test_identical_consecutive_sections(self):
        with self.assertRaises(ValueError):
            Loft([square(1.0), square(1.0)], [frame_at_height(0.0), frame_at_height(0.0)])

    def test_serialization(self):
        loft = Loft([square(1.0), square(0.5)], [frame_at_height(0.0), frame_at_height(1.0)], name="loft")
        dict_ = loft.to_dict()
        new_loft = deserialize(dict_)
        self.assertIsInstance(new_loft, Loft)
        self.assertEqual(len(new_loft.faces), 6)
        self.assertAlmostEqual(new_loft.volume(), loft.volume(), places=6)

    def test_copy_and_frame_mapping(self):
        loft = Loft([square(1.0), square(0.5)], [frame_at_height(0.0), frame_at_height(1.0)])
        copied_loft = loft.copy()
        self.assertIsInstance(copied_loft, Loft)
        self.assertAlmostEqual(copied_loft.volume(), loft.volume(), places=6)

        new_frame = design3d.Frame3D(design3d.Point3D(1.0, 2.0, 3.0), design3d.X3D, design3d.Y3D, design3d.Z3D)
        mapped_loft = loft.frame_mapping(new_frame, "old")
        self.assertIsInstance(mapped_loft, Loft)
        self.assertTrue(mapped_loft.point_inside(design3d.Point3D(1.0, 2.0, 3.5)))
        self.assertAlmostEqual(mapped_loft.volume(), loft.volume(), places=6)


class TestLoftFaces(unittest.TestCase):
    def test_open_wires(self):
        # Open wires give an open shell: here a two-faced "roof" whose ridge gets lower along X.
        wire1 = wires.Wire3D.from_points(
            [design3d.Point3D(0.0, -1.0, 0.0), design3d.Point3D(0.0, 0.0, 1.0), design3d.Point3D(0.0, 1.0, 0.0)]
        )
        wire2 = wires.Wire3D.from_points(
            [design3d.Point3D(2.0, -1.0, 0.0), design3d.Point3D(2.0, 0.0, 0.5), design3d.Point3D(2.0, 1.0, 0.0)]
        )
        loft_shell = shells.OpenShell3D(loft_faces([wire1, wire2]))
        self.assertEqual(len(loft_shell.faces), 2)
        # Ridge at mid-length
        ridge_point = design3d.Point3D(1.0, 0.0, 0.75)
        self.assertTrue(any(face.point_belongs(ridge_point) for face in loft_shell.faces))

    def test_adjacent_faces_share_their_edges(self):
        sections = [square(1.0).to_3d(design3d.Point3D(0.0, 0.0, z), design3d.X3D, design3d.Y3D) for z in (0, 1, 3)]
        lateral_faces = loft_faces(sections)
        for face, next_face in zip(lateral_faces, lateral_faces[1:] + lateral_faces[:1]):
            for v in (0.0, 0.2, 0.5, 0.9, 1.0):
                point = face.surface3d.point2d_to_3d(design3d.Point2D(1.0, v))
                next_point = next_face.surface3d.point2d_to_3d(design3d.Point2D(0.0, v))
                self.assertTrue(point.is_close(next_point, 1e-9))


if __name__ == "__main__":
    unittest.main()
