"""
Unit testing of the babylonjs data and html pages of the models.
"""

import unittest

import design3d
import design3d.primitives3d as p3d
from design3d.core import VolumeModel


class TestBabylonPage(unittest.TestCase):
    def setUp(self):
        self.model = VolumeModel([p3d.Block(design3d.OXYZ, name="block")], name="model")

    def test_embedded_page(self):
        data = self.model.babylon_data()
        page = VolumeModel.babylonjs_script(data, title="model", use_cdn=False)
        self.assertNotIn("cdn.babylonjs.com", page)


if __name__ == "__main__":
    unittest.main()
