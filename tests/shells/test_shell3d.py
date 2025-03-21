import unittest
import os

from dessia_common.core import DessiaObject
import design3d
from design3d import shells

folder = os.path.join(os.path.dirname(os.path.realpath(__file__)))


class TestShell3D(unittest.TestCase):
    def test_from_faces(self):
        openshell = DessiaObject.from_json(os.path.join(folder, "open_shell.json"))
        closedshell = DessiaObject.from_json(os.path.join(folder, "closed_shell.json"))
        fm_closedshell = closedshell.frame_mapping(design3d.Frame3D(design3d.Point3D(0.5, 0.5, 0.5),
                                                                   design3d.X3D, design3d.Y3D, design3d.Z3D), 'new')
        from_faces = shells.Shell3D.from_faces(openshell.faces + fm_closedshell.faces)
        self.assertEqual(from_faces[0], openshell)
        self.assertEqual(from_faces[1], fm_closedshell)


if __name__ == '__main__':
    unittest.main()
