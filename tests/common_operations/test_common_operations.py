import unittest

import design3d
from design3d.models.open_rounded_line_segments import open_rounded_line_segements
from design3d.surfaces import Plane3D
from design3d.utils.common_operations import split_wire_by_plane


class TestCommonOperations(unittest.TestCase):
    def test_split_wire_by_plane(self):
        plane = Plane3D.from_plane_vectors(design3d.Point3D(0.4, 0.4, 0.2), design3d.Vector3D(1, 0, 0),
                                           design3d.Vector3D(0, 1, 0))
        wire1, wire2 = split_wire_by_plane(open_rounded_line_segements, plane)
        self.assertEqual(wire1.length(), 1.4187473149621863)
        self.assertAlmostEqual(wire2.length(), 0.6182864075957109)


if __name__ == "__main__":
    unittest.main()
