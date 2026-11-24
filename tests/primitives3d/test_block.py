import unittest

import design3d
from design3d.core import BoundingBox
from design3d.primitives3d import Block


class TestBlock(unittest.TestCase):
    def setUp(self) -> None:
        self.block = Block(frame=design3d.OXYZ)

    def test_from_bounding_box(self):
        bounding_box = BoundingBox(-0.5, 0.5, -0.5, 0.5, -0.5, 0.5)

        block = Block.from_bounding_box(bounding_box)
        self.assertEqual(self.block.frame, block.frame)

    def test_get_bounding_box(self):
        bbox1 = BoundingBox(
            -0.0271021, 1.0271020999999998, -0.4024024, 0.8024024000000001, -0.0261011, 0.5261011000000001
        )
        block = Block.from_bounding_box(bbox1)
        bbox2 = block.bounding_box

        self.assertTrue(bbox1.is_close(bbox2))

    def test_get_bounding_box_rotated(self):
        # Block of size 0.3 x 0.2 x 0.1 whose u axis is along Y and v axis along -X
        frame = design3d.Frame3D(
            design3d.Point3D(1.0, 0.0, 0.5), 0.3 * design3d.Y3D, -0.2 * design3d.X3D, 0.1 * design3d.Z3D
        )
        block = Block(frame)
        self.assertTrue(block.bounding_box.is_close(BoundingBox(0.9, 1.1, -0.15, 0.15, 0.45, 0.55)))

        # Block rotated by 45 degrees around Z: the bounding box encloses its vertices
        frame = design3d.Frame3D(design3d.O3D, design3d.Vector3D(1, 1, 0), design3d.Vector3D(-1, 1, 0), design3d.Z3D)
        block = Block(frame)
        self.assertTrue(block.bounding_box.is_close(BoundingBox(-1.0, 1.0, -1.0, 1.0, -0.5, 0.5)))
