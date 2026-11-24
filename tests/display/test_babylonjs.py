"""
Unit testing of the babylonjs data and html pages of the models.
"""

import unittest

import design3d
import design3d.primitives3d as p3d
from design3d.core import MovingVolumeModel, VolumeModel


class TestBabylonPage(unittest.TestCase):
    def setUp(self):
        self.model = VolumeModel([p3d.Block(design3d.OXYZ, name="block")], name="model")

    def test_embedded_page(self):
        data = self.model.babylon_data()
        page = VolumeModel.babylonjs_script(data, title="model", use_cdn=False)
        self.assertNotIn("cdn.babylonjs.com", page)

    def test_moving_volume_model_page(self):
        block = p3d.Block(design3d.OXYZ, name="block")
        frames = [[design3d.OXYZ.translation(design3d.Point3D(0.5 * i, 0, 0))] for i in range(3)]
        data = MovingVolumeModel([block], frames).babylon_data()
        # numpy floats are written as np.float64(...) in the page, which is not valid javascript
        self.assertIs(type(data["max_length"]), float)
        page = MovingVolumeModel.babylonjs_script(data, title="moving")
        self.assertNotIn("np.", page)


if __name__ == "__main__":
    unittest.main()
