"""
Tests for RevolvedProfile.
"""

import io
import math
import unittest

import design3d
import design3d.step
from design3d import wires
from design3d.core import VolumeModel
from design3d.primitives3d import RevolvedProfile


class TestRevolvedProfile(unittest.TestCase):
    def setUp(self):
        # Trapezoidal section away from the axis: its slanted sides give conical faces whose apex is not on the
        # revolution axis, hence a non-zero ref_radius.
        contour = wires.ClosedPolygon2D(
            [
                design3d.Point2D(-0.1, 0.25),
                design3d.Point2D(0.0, 0.2),
                design3d.Point2D(0.0, 0.15),
                design3d.Point2D(-0.1, 0.18),
            ]
        )
        frame = design3d.Frame3D(design3d.O3D, design3d.X3D, design3d.Z3D, -design3d.Y3D)
        self.profile = RevolvedProfile(frame, contour, design3d.O3D, design3d.X3D, angle=math.pi)

    def test_step_round_trip_conical_faces(self):
        stream = io.StringIO()
        VolumeModel([self.profile]).to_step_stream(stream)
        step = design3d.step.Step(stream.getvalue().splitlines(keepends=True))
        imported_shell = step.to_volume_model().primitives[0]

        def conical_surfaces(shell):
            return sorted(
                (face.surface3d for face in shell.faces if face.__class__.__name__ == "ConicalFace3D"),
                key=lambda surface: surface.ref_radius,
            )

        original_cones = conical_surfaces(self.profile)
        imported_cones = conical_surfaces(imported_shell)
        self.assertEqual(len(original_cones), 2)
        self.assertEqual(len(imported_cones), 2)
        # One of the cones narrows along its axis: its semi_angle is negative, which STEP forbids
        self.assertTrue(any(cone.semi_angle < 0 for cone in original_cones))
        for original, imported in zip(original_cones, imported_cones):
            self.assertGreater(imported.semi_angle, 0.0)
            # Same cone: same apex, same axis line, same opening and same section in the reference plane
            self.assertTrue(imported.apex.is_close(original.apex))
            self.assertAlmostEqual(abs(imported.frame.w.dot(original.frame.w)), 1.0, places=6)
            self.assertAlmostEqual(imported.semi_angle, abs(original.semi_angle), places=6)
            self.assertAlmostEqual(imported.ref_radius, original.ref_radius, places=6)

        # The imported faces must lie on the same radii as the original ones (0.15 to 0.25 from the axis)
        for face in imported_shell.faces:
            for point in face.triangulation().vertices:
                radius = math.hypot(point[1], point[2])
                self.assertGreater(radius, 0.15 - 1e-6)
                self.assertLess(radius, 0.25 + 1e-6)


if __name__ == "__main__":
    unittest.main()
