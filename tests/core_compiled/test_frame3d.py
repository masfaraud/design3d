import unittest
import math
import design3d


class TestFrame3D(unittest.TestCase):
    local_frame = design3d.Frame3D(
        design3d.Point3D(0.1, 0.3, 0.6),
        design3d.Y3D,
        design3d.Z3D,
        design3d.X3D,
    )

    def test_global_to_local_coordinates(self):
        vector_global = design3d.Vector3D(3, 4, 5)
        vector_local = self.local_frame.global_to_local_coordinates(vector_global)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_local.x, 4 - 0.3)
        self.assertEqual(vector_local.y, 5 - 0.6)
        self.assertEqual(vector_local.z, 3 - 0.1)

    def test_local_to_global_coordinates(self):
        vector_local = design3d.Vector3D(4 - 0.3, 5 - 0.6, 3 - 0.1)
        vector_global = self.local_frame.local_to_global_coordinates(vector_local)

        # Check that the converted vector has the expected coordinates
        self.assertEqual(vector_global.x, 3)
        self.assertEqual(vector_global.y, 4)
        self.assertEqual(vector_global.z, 5)

    def test_from_step(self):
        arguments = [' ', 14, '$', '$']
        object_dict = {14: design3d.O3D}
        frame = design3d.Frame3D.from_step(arguments, object_dict)
        self.assertEqual(frame, design3d.OXYZ)

        arguments = [' ', 43, 44, 45]
        object_dict = {43: design3d.Point3D(-5.829000000001e0, -9.909144910505e-1, 8.766383164265e-1),
                       44: design3d.Vector3D(0.e0, 6.625993710787e-1, 7.489740138657e-1),
                       45: design3d.Vector3D(-5.829000000001e0, -9.909144910505e-1, 8.766383164265e-1)
                       }
        frame = design3d.Frame3D.from_step(arguments, object_dict)
        self.assertEqual(frame.w, object_dict[44])
        self.assertEqual(frame.origin, object_dict[43])

        arguments = [' ', 20, 21, '$']
        object_dict = {20: design3d.O3D,
                       21: design3d.Y3D
                       }
        frame = design3d.Frame3D.from_step(arguments, object_dict)
        self.assertTrue(frame.w.is_close(object_dict[21]))

    def test_to_step(self):
        step_content, _ = design3d.OXYZ.to_step(10)
        expected_result = "#11 = CARTESIAN_POINT('',(0.0,0.0,0.0));\n" \
                          "#12 = DIRECTION('',(0.0,0.0,1.0));\n" \
                          "#13 = DIRECTION('',(1.0,0.0,0.0));\n" \
                          "#14 = AXIS2_PLACEMENT_3D('',#11,#12,#13);\n"
        self.assertEqual(step_content, expected_result)

        step_content, _ = design3d.OYZX.to_step(10)
        expected_result = "#11 = CARTESIAN_POINT('',(0.0,0.0,0.0));\n" \
                          "#12 = DIRECTION('',(1.0,0.0,0.0));\n" \
                          "#13 = DIRECTION('',(0.0,1.0,0.0));\n" \
                          "#14 = AXIS2_PLACEMENT_3D('',#11,#12,#13);\n"
        self.assertEqual(step_content, expected_result)

    def test_rotation(self):
        axis = design3d.X3D
        rot1 = design3d.OXYZ.rotation(design3d.Point3D(0, -1, 0), axis, 0.5*math.pi)
        self.assertTrue(rot1.origin.is_close(design3d.Point3D(0, -1, 1)))
        self.assertTrue(rot1.v.is_close(design3d.Z3D))
        self.assertTrue(rot1.w.is_close(-design3d.Y3D))

        axis = design3d.Vector3D(1/math.sqrt(2), 0, 1/math.sqrt(2))
        rot2 = design3d.OXYZ.rotation(design3d.Point3D(0, -1, 0), axis, 0.5*math.pi)
        self.assertTrue(rot2.origin.is_close(design3d.Point3D(-1/math.sqrt(2), -1, 1/math.sqrt(2))))
        self.assertTrue(rot2.v.is_close(design3d.Vector3D(-1/math.sqrt(2), 0, 1/math.sqrt(2))))


if __name__ == "__main__":
    unittest.main()
