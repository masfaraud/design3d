import unittest
import design3d
import design3d.edges
from design3d.core import CompositePrimitive3D


class TestCompositePrimitive3D(unittest.TestCase):
    def setUp(self):
        self.primitives = [design3d.edges.LineSegment3D(design3d.O3D, design3d.Point3D(4, 2, 1))]
        self.composite_3d = CompositePrimitive3D(self.primitives, name="test")

    def test_plot(self):
        ax = self.composite_3d.plot()

        for ls, line in zip(self.composite_3d.primitives, ax.lines):
            data = line.get_data_3d()

            for i in range(3):
                self.assertListEqual(data[i].tolist(), [ls.start[i], ls.end[i]])


if __name__ == "__main__":
    unittest.main()
