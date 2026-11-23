import os
import tempfile
import unittest

import design3d as d3d
from design3d import faces, stl

POINTS = [
    d3d.Point3D(0.0, 0.0, 0.0),
    d3d.Point3D(1.0, 0.0, 0.0),
    d3d.Point3D(0.0, 1.0, 0.0),
    d3d.Point3D(0.0, 0.0, 1.0),
]


def tetrahedron_stl():
    point0, point1, point2, point3 = POINTS
    triangles = [
        faces.Triangle3D(point0, point2, point1),
        faces.Triangle3D(point0, point1, point3),
        faces.Triangle3D(point0, point3, point2),
        faces.Triangle3D(point1, point2, point3),
    ]
    return stl.Stl(triangles, name="tetrahedron")


class TestStl(unittest.TestCase):
    def setUp(self):
        self.stl = tetrahedron_stl()
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)

    def test_binary_file_round_trip(self):
        filepath = os.path.join(self.tempdir.name, "tetrahedron")
        self.stl.save_to_binary_file(filepath, distance_multiplier=1000)
        filepath += ".stl"
        self.assertTrue(stl.is_binary(filepath))

        read_stl = stl.Stl.load_from_file(filepath, distance_multiplier=0.001)
        self.assertEqual(len(read_stl.triangles), 4)
        for read_triangle, triangle in zip(read_stl.triangles, self.stl.triangles):
            for read_point, point in zip(read_triangle.points, triangle.points):
                self.assertTrue(read_point.is_close(point))

        points = stl.Stl.points_from_file(filepath, distance_multiplier=0.001)
        self.assertEqual(len(points), 12)
        self.assertTrue(points[0].is_close(POINTS[0]))
        self.assertTrue(points[-1].is_close(POINTS[3]))

    def test_get_normals(self):
        points_normals = self.stl.get_normals()
        self.assertEqual(len(points_normals), 4)
        self.assertEqual(len(self.stl.normals), 4)
        for normal in self.stl.normals:
            self.assertAlmostEqual(normal.norm(), 1.0)

    def test_clean_flat_triangles(self):
        flat_triangle = faces.Triangle3D(POINTS[0], POINTS[1], d3d.Point3D(0.5, 1e-14, 0.0))
        dirty_stl = stl.Stl(self.stl.triangles + [flat_triangle])
        clean_stl = dirty_stl.clean_flat_triangles()
        self.assertEqual(len(clean_stl.triangles), 4)


if __name__ == "__main__":
    unittest.main()
