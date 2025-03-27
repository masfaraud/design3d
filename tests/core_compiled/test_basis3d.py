import unittest

import design3d


class TestBasis3D(unittest.TestCase):
    local_basis = design3d.Basis3D(design3d.Y3D, design3d.Z3D, design3d.X3D)

    def test_is_orthonormal(self):
        self.assertTrue(self.local_basis.is_orthonormal())

    def test_global_to_local_coordinates(self):
        vector_global = design3d.Vector3D(3, 4, 5)
        vector_local = self.local_basis.global_to_local_coordinates(vector_global)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_local.x, 4)
        self.assertEqual(vector_local.y, 5)
        self.assertEqual(vector_local.z, 3)

    def test_local_to_global_coordinates(self):
        vector_local = design3d.Vector3D(4, 5, 3)
        vector_global = self.local_basis.local_to_global_coordinates(vector_local)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_global.x, 3)
        self.assertEqual(vector_global.y, 4)
        self.assertEqual(vector_global.z, 5)


if __name__ == "__main__":
    unittest.main()
