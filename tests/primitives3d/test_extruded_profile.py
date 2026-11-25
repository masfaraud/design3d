"""Tests for design3d.primitives3d.ExtrudedProfile, including symmetric and draft extrusions."""

import math
import unittest

import design3d
from design3d import curves, faces, shells, wires
from design3d.primitives2d import RoundedRectangle2D, Slot2D
from design3d.primitives3d import ExtrudedProfile

LENGTH = 0.5
SQUARE = wires.Contour2D.from_points(
    [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(1, 1), design3d.Point2D(0, 1)]
)
CIRCLE = wires.Contour2D.from_circle(curves.Circle2D(design3d.OXY, 0.5))
# Draft angle giving a 0.1 offset over the extrusion length.
DRAFT_ANGLE = math.atan(0.1 / LENGTH)


def frustum_volume(length, area_1, area_2):
    return length / 3 * (area_1 + area_2 + math.sqrt(area_1 * area_2))


class TestExtrudedProfile(unittest.TestCase):
    def _assert_z_bounds(self, profile, z_min, z_max):
        bounding_box = profile.bounding_box
        self.assertAlmostEqual(bounding_box.zmin, z_min)
        self.assertAlmostEqual(bounding_box.zmax, z_max)

    def _assert_volume(self, profile, expected_volume, check_shell_volume=True):
        """
        Checks the analytical volume, and the volume of the closed shell computed from its faces.

        The shell volume discretizes curved faces, hence a relative tolerance. It is wrong for shells with holes, even
        for a straight extrusion, so it is not checked on those.
        """
        self.assertAlmostEqual(profile.volume(), expected_volume)
        if check_shell_volume:
            self.assertAlmostEqual(shells.ClosedShell3D.volume(profile), expected_volume, delta=1e-2 * expected_volume)

    def test_straight_extrusion(self):
        profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], LENGTH)
        self.assertEqual(len(profile.faces), 6)
        self._assert_z_bounds(profile, 0.0, LENGTH)
        self._assert_volume(profile, LENGTH)

    def test_symmetric(self):
        profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], LENGTH, symmetric=True)
        self.assertEqual(len(profile.faces), 6)
        self._assert_z_bounds(profile, -0.5 * LENGTH, 0.5 * LENGTH)
        self._assert_volume(profile, LENGTH)

    def test_negative_length(self):
        """A negative length extrudes along -w, with or without draft, and gives a negative volume."""
        for draft_angle in (0.0, DRAFT_ANGLE):
            profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], -LENGTH, draft_angle=draft_angle)
            self._assert_z_bounds(profile, -LENGTH, 0.0)
            self.assertLess(profile.volume(), 0.0)
            self.assertAlmostEqual(-profile.volume(), abs(shells.ClosedShell3D.volume(profile)))

    def test_draft_square(self):
        profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], LENGTH, draft_angle=DRAFT_ANGLE)
        self._assert_z_bounds(profile, 0.0, LENGTH)
        self.assertAlmostEqual(profile.bounding_box.xmin, 0.0)
        self.assertTrue(all(isinstance(face, faces.PlaneFace3D) for face in profile.faces))
        self._assert_volume(profile, frustum_volume(LENGTH, 1.0, 0.8**2))

    def test_draft_circle(self):
        profile = ExtrudedProfile(design3d.OXYZ, CIRCLE, [], LENGTH, draft_angle=DRAFT_ANGLE)
        self.assertTrue(any(isinstance(face, faces.ConicalFace3D) for face in profile.faces))
        self._assert_volume(profile, frustum_volume(LENGTH, math.pi * 0.5**2, math.pi * 0.4**2))

    def test_negative_draft_enlarges(self):
        profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], LENGTH, draft_angle=-DRAFT_ANGLE)
        self.assertAlmostEqual(profile.bounding_box.xmin, -0.1)
        self._assert_volume(profile, frustum_volume(LENGTH, 1.0, 1.2**2))

    def test_draft_and_symmetric(self):
        profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], LENGTH, draft_angle=DRAFT_ANGLE, symmetric=True)
        self._assert_z_bounds(profile, -0.5 * LENGTH, 0.5 * LENGTH)
        # Each half shrinks by 0.05 away from the sketch plane.
        self._assert_volume(profile, 2 * frustum_volume(0.5 * LENGTH, 1.0, 0.9**2))

    def test_draft_rounded_profile_with_hole(self):
        """The outer contour shrinks and the hole widens: Simpson's rule is exact for offset sections."""
        outer = RoundedRectangle2D(1.0, 0.6, 0.1)
        hole = Slot2D(0.4, 0.2)
        profile = ExtrudedProfile(design3d.OXYZ, outer, [hole], LENGTH, draft_angle=math.atan(0.04 / LENGTH))

        def outer_area(offset):
            return RoundedRectangle2D(1.0 - 2 * offset, 0.6 - 2 * offset, 0.1 - offset).area()

        def section_area(offset):
            return outer_area(offset) - Slot2D(0.4 + 2 * offset, 0.2 + 2 * offset).area()

        expected_volume = LENGTH / 6 * (section_area(0) + 4 * section_area(0.02) + section_area(0.04))
        self._assert_volume(profile, expected_volume, check_shell_volume=False)
        self.assertEqual(len(profile.faces), 2 + 8 + 4)

        # Without the hole, the shell volume checks the geometry of the faces.
        outer_profile = ExtrudedProfile(design3d.OXYZ, outer, [], LENGTH, draft_angle=math.atan(0.04 / LENGTH))
        self._assert_volume(outer_profile, LENGTH / 6 * (outer_area(0) + 4 * outer_area(0.02) + outer_area(0.04)))

    def test_draft_too_large(self):
        with self.assertRaises(ValueError):
            ExtrudedProfile(design3d.OXYZ, Slot2D(1.0, 0.2), [], LENGTH, draft_angle=math.atan(0.15 / LENGTH))

    def test_parameters_are_kept(self):
        profile = ExtrudedProfile(design3d.OXYZ, SQUARE, [], LENGTH, draft_angle=DRAFT_ANGLE, symmetric=True)
        offset = design3d.Vector3D(1.0, 0.0, 0.0)
        for new_profile in (
            profile.copy(),
            profile.translation(offset),
            profile.rotation(design3d.O3D, design3d.Z3D, 0.3),
            profile.frame_mapping(design3d.OXYZ.translation(offset), "new"),
            ExtrudedProfile.dict_to_object(profile.to_dict()),
        ):
            self.assertEqual((new_profile.draft_angle, new_profile.symmetric), (DRAFT_ANGLE, True))
            self.assertAlmostEqual(new_profile.volume(), profile.volume())


if __name__ == "__main__":
    unittest.main()
