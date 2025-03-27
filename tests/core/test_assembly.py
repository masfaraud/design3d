import unittest
import design3d
import design3d.primitives3d as p3d
import design3d.core


class TestAssembly(unittest.TestCase):
    def test_bounding_box(self):
        box1 = p3d.Block(design3d.OXYZ)
        components = [box1, box1]
        positions = [design3d.OXYZ, design3d.Frame3D(design3d.Point3D(0, 0, 1), design3d.X3D, design3d.Y3D, design3d.Z3D)]
        assembly = design3d.core.Assembly(components, positions)
        self.assertAlmostEqual(assembly.bounding_box.volume(), 2.0)  # add assertion here


if __name__ == '__main__':
    unittest.main()
