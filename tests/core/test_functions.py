"""
Unit tests for functions defined in design3d.core.py
"""
import unittest
import design3d
from design3d.core import delete_double_point, step_ids_to_str


class TestDeleteDoublePoint(unittest.TestCase):
    def setUp(self):
        self.points = [
            design3d.Point3D(0.0, 0.0, 0.0),
            design3d.Point3D(1.0, 1.0, 1.0),
            design3d.Point3D(0.0, 0.0, 0.0),
            design3d.Point3D(2.0, 2.0, 2.0),
        ]

    def test_delete_double_point(self):
        result = delete_double_point(self.points)

        self.assertEqual(len(result), 3)
        self.assertTrue(design3d.Point3D(0.0, 0.0, 0.0) in result)
        self.assertTrue(design3d.Point3D(1.0, 1.0, 1.0) in result)
        self.assertTrue(design3d.Point3D(2.0, 2.0, 2.0) in result)


class TestStepIdsToStr(unittest.TestCase):
    ids_0 = [0]
    ids_1 = [1, 2, 3, 4, 5]
    ids_2 = [11, 22, 33, 44, 55]

    def test_step_ids_to_str(self):
        self.assertEqual(step_ids_to_str(self.ids_0), "#0")
        self.assertEqual(step_ids_to_str(self.ids_1), "#1,#2,#3,#4,#5")
        self.assertEqual(step_ids_to_str(self.ids_2), "#11,#22,#33,#44,#55")


if __name__ == "__main__":
    unittest.main()
