import unittest

import design3d
from design3d import curves, edges, faces, primitives3d, wires
from design3d.primitives3d import Sweep


def rounded_path() -> primitives3d.OpenRoundedLineSegments3D:
    return primitives3d.OpenRoundedLineSegments3D(
        [design3d.Point3D(1.0, 1.0, 0.0), design3d.Point3D(1.0, 0.5, 0.0), design3d.Point3D(0.5, 0.5, 0.0)],
        {"1": 0.2},
    )


def circular_section() -> wires.Contour2D:
    return wires.Contour2D([curves.Circle2D(design3d.OXY, 0.05)])


class TestSweep(unittest.TestCase):
    def test_init(self):
        path = primitives3d.OpenRoundedLineSegments3D(
            [design3d.Point3D(1.0, 1.0, 0.0), design3d.Point3D(1.0, 0.5, 0.0), design3d.Point3D(0.5, 0.5, 0.0)],
            {"1": 0.2},
        )
        section = wires.Contour2D([curves.Circle2D(design3d.OXY, 0.05)])
        sweep = Sweep(section, path)
        self.assertEqual(len(sweep.faces), 5)
        for face, expected_face_class in zip(
            sweep.faces,
            [
                faces.PlaneFace3D,
                faces.CylindricalFace3D,
                faces.ToroidalFace3D,
                faces.CylindricalFace3D,
                faces.PlaneFace3D,
            ],
        ):
            self.assertTrue(isinstance(face, expected_face_class))

    def test_to_dict(self):
        dict_ = Sweep(circular_section(), rounded_path(), name="pipe").to_dict()
        self.assertEqual(dict_["name"], "pipe")
        self.assertIn("wire3d", dict_)
        self.assertIn("contour2d", dict_)

    def test_copy(self):
        sweep = Sweep(circular_section(), rounded_path())
        copied_sweep = sweep.copy()
        self.assertIsInstance(copied_sweep, Sweep)
        self.assertEqual(len(copied_sweep.faces), len(sweep.faces))
        self.assertTrue(copied_sweep.wire3d.primitives[0].start.is_close(sweep.wire3d.primitives[0].start))

    def test_frame_mapping(self):
        sweep = Sweep(circular_section(), rounded_path())
        offset = design3d.Vector3D(0.1, 0.2, 0.3)
        frame = design3d.Frame3D(design3d.O3D + offset, design3d.X3D, design3d.Y3D, design3d.Z3D)
        mapped_sweep = sweep.frame_mapping(frame, "old")
        self.assertIsInstance(mapped_sweep, Sweep)
        self.assertTrue(mapped_sweep.wire3d.primitives[0].start.is_close(sweep.wire3d.primitives[0].start + offset))

    def test_starting_frame_not_on_path(self):
        starting_frame = design3d.Frame3D(design3d.O3D, design3d.X3D, design3d.Z3D, -design3d.Y3D)
        with self.assertRaises(ValueError):
            Sweep(circular_section(), rounded_path(), starting_frame)

    def test_path_not_c1_continuous(self):
        # Two line segments with a sharp corner
        path = wires.Wire3D(
            [
                edges.LineSegment3D(design3d.Point3D(0.0, 0.0, 0.0), design3d.Point3D(1.0, 0.0, 0.0)),
                edges.LineSegment3D(design3d.Point3D(1.0, 0.0, 0.0), design3d.Point3D(1.0, 1.0, 0.0)),
            ]
        )
        with self.assertRaises(ValueError):
            Sweep(circular_section(), path)


if __name__ == "__main__":
    unittest.main()
