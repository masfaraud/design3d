import unittest

import design3d


class TestBasis2D(unittest.TestCase):
    local_basis = design3d.Basis2D(design3d.Y2D, design3d.X2D)

    def test_global_to_local_coordinates(self):
        vector_global = design3d.Vector2D(3, 4)
        vector_local = self.local_basis.global_to_local_coordinates(vector_global)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_local.x, 4)
        self.assertEqual(vector_local.y, 3)

    def test_local_to_global_coordinates(self):
        vector_local = design3d.Vector2D(4, 3)
        vector_global = self.local_basis.local_to_global_coordinates(vector_local)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_global.x, 3)
        self.assertEqual(vector_global.y, 4)


if __name__ == "__main__":
    unittest.main()
