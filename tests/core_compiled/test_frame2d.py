import unittest
import math
import design3d


class TestFrame2D(unittest.TestCase):
    local_frame = design3d.Frame2D(design3d.Point2D(0.1, 0.3), design3d.Y2D, design3d.X2D)

    def test_global_to_local_coordinates(self):
        vector_global = design3d.Vector2D(3, 4)
        vector_local = self.local_frame.global_to_local_coordinates(vector_global)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_local.x, 3.7)
        self.assertEqual(vector_local.y, 2.9)

    def test_local_to_global_coordinates(self):
        vector_local = design3d.Vector2D(3.7, 2.9)
        vector_global = self.local_frame.local_to_global_coordinates(vector_local)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_global.x, 3)
        self.assertEqual(vector_global.y, 4)


    def test_rotation(self):
        center = design3d.Point2D(-1, 0)
        rot1 = design3d.OXY.rotation(center, 0.5 * math.pi, rotate_basis=True)
        self.assertTrue(rot1.origin.is_close(design3d.Point2D(-1, 1)))
        self.assertTrue(rot1.u.is_close(design3d.Y2D))
        self.assertTrue(rot1.v.is_close(-design3d.X2D))

        center = design3d.Point2D(-1, 0)
        rot2 = design3d.OXY.rotation(center, 0.25 * math.pi, rotate_basis=True)
        self.assertTrue(rot2.origin.is_close(design3d.Point2D(1/math.sqrt(2) - 1, 1/math.sqrt(2))))
        self.assertTrue(rot2.u.is_close(design3d.Vector2D(1/math.sqrt(2), 1/math.sqrt(2))))

        center = design3d.Point2D(-1, 0)
        rot2 = design3d.OXY.rotation(center, 0.25 * math.pi, rotate_basis=False)
        self.assertTrue(rot2.origin.is_close(design3d.Point2D(1/math.sqrt(2) - 1, 1/math.sqrt(2))))
        self.assertEqual(rot2.u, rot2.u)
        self.assertEqual(rot2.v, rot2.v)


if __name__ == "__main__":
    unittest.main()
