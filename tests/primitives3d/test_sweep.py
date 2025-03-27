import unittest

import design3d
from design3d import wires, curves, faces, primitives3d
from design3d.primitives3d import Sweep


class TestSweep(unittest.TestCase):
    def test_init(self):
        path = primitives3d.OpenRoundedLineSegments3D([design3d.Point3D(1.0, 1.0, 0.0), design3d.Point3D(1.0, 0.5, 0.0),
                                                      design3d.Point3D(0.5, 0.5, 0.0)], {"1": 0.2})
        section = wires.Contour2D([curves.Circle2D(design3d.OXY, 0.05)])
        sweep = Sweep(section, path)
        self.assertEqual(len(sweep.faces), 5)
        for face, expected_face_class in zip(sweep.faces, [faces.PlaneFace3D, faces.CylindricalFace3D,
                                                           faces.ToroidalFace3D, faces.CylindricalFace3D,
                                                           faces.PlaneFace3D]):
            self.assertTrue(isinstance(face, expected_face_class))


if __name__ == '__main__':
    unittest.main()
