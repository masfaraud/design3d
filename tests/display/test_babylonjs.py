"""
Unit testing of the babylonjs data and html pages of the models.
"""

import unittest

import design3d
import design3d.primitives3d as p3d
from design3d.core import Assembly, Compound, MovingVolumeModel, VolumeModel, primitives_babylon_data
from design3d.edges import LineSegment3D


class TestBabylonTree(unittest.TestCase):
    def setUp(self):
        self.block = p3d.Block(design3d.OXYZ, name="block")
        self.cylinder = p3d.Cylinder(design3d.OXYZ, radius=0.3, length=2.0, name="shaft")
        self.sub_assembly = Assembly(
            [self.block, self.cylinder],
            [design3d.OXYZ, design3d.OXYZ.translation(design3d.Point3D(0, 0, 1))],
            name="sub assembly",
        )
        self.sphere = p3d.Sphere(design3d.O3D, 0.5)
        self.assembly = Assembly(
            [self.sub_assembly, self.sub_assembly, self.sphere],
            [design3d.OXYZ, design3d.OXYZ.translation(design3d.Point3D(3, 0, 0)), design3d.OXYZ],
            name="top",
        )

    def test_flat_volume_model(self):
        data = VolumeModel([self.block, self.cylinder]).babylon_data()
        self.assertEqual(len(data["meshes"]), 2)
        self.assertEqual(
            data["tree"],
            [
                {"name": "block", "type": "Block", "meshes": [0], "lines": [], "children": []},
                {"name": "shaft", "type": "Cylinder", "meshes": [1], "lines": [], "children": []},
            ],
        )

    def test_nested_assemblies(self):
        data = VolumeModel([self.block, self.assembly]).babylon_data()
        self.assertEqual(len(data["meshes"]), 6)
        block_node, top_node = data["tree"]
        self.assertEqual(block_node["meshes"], [0])
        self.assertEqual((top_node["name"], top_node["type"], top_node["meshes"]), ("top", "Assembly", []))
        first, second, sphere = top_node["children"]
        # Mesh indices of the sub assemblies are shifted after the meshes already collected
        self.assertEqual([child["meshes"] for child in first["children"]], [[1], [2]])
        self.assertEqual([child["meshes"] for child in second["children"]], [[3], [4]])
        self.assertEqual([child["name"] for child in second["children"]], ["block", "shaft"])
        self.assertEqual((sphere["name"], sphere["type"], sphere["meshes"]), ("", "Sphere", [5]))

    def test_compound(self):
        compound = Compound([self.block, self.cylinder], name="compound")
        data = VolumeModel([compound]).babylon_data()
        self.assertEqual(data["tree"][0]["type"], "Compound")
        self.assertEqual([child["meshes"] for child in data["tree"][0]["children"]], [[0], [1]])

    def test_lines(self):
        segment = LineSegment3D(design3d.O3D, design3d.Point3D(1, 0, 0), name="segment")
        data = primitives_babylon_data([self.block, segment, segment])
        self.assertEqual(len(data["lines"]), 2)
        self.assertEqual([node["lines"] for node in data["tree"]], [[], [0], [1]])
        self.assertEqual(data["tree"][1]["type"], "LineSegment3D")

    def test_sub_model_without_tree(self):
        class LegacyModel:
            """Model whose babylon_data has no scene tree."""

            def __init__(self, primitives):
                self.primitives = primitives

            def babylon_data(self, merge_meshes=True):
                data = primitives_babylon_data(self.primitives, merge_meshes=merge_meshes)
                del data["tree"]
                return data

        data = primitives_babylon_data([self.block, LegacyModel([self.block, self.cylinder])])
        self.assertEqual(data["tree"][1]["type"], "LegacyModel")
        self.assertEqual(data["tree"][1]["meshes"], [1, 2])

    def test_points_are_not_nodes(self):
        data = primitives_babylon_data([self.block, design3d.Point3D(5, 0, 0)])
        self.assertEqual(len(data["tree"]), 1)
        # The point is still taken into account in the size of the scene
        self.assertGreater(data["max_length"], 4.9)


class TestBabylonPage(unittest.TestCase):
    def setUp(self):
        self.model = VolumeModel([p3d.Block(design3d.OXYZ, name="block")], name="model")

    def test_cdn_page(self):
        data = self.model.babylon_data()
        page = VolumeModel.babylonjs_script(data, title="model", use_cdn=True)
        self.assertIn("function design3dViewer", page)
        self.assertIn("#d3d-panel", page)
        self.assertIn("'debug': 0", page)
        self.assertNotIn("scene.debugLayer.show();", page)

    def test_embedded_page(self):
        data = self.model.babylon_data()
        page = VolumeModel.babylonjs_script(data, title="model", use_cdn=False)
        self.assertIn("function design3dViewer", page)
        self.assertNotIn("cdn.babylonjs.com", page)

    def test_moving_volume_model_page(self):
        block = p3d.Block(design3d.OXYZ, name="block")
        frames = [[design3d.OXYZ.translation(design3d.Point3D(0.5 * i, 0, 0))] for i in range(3)]
        data = MovingVolumeModel([block], frames).babylon_data()
        # numpy floats are written as np.float64(...) in the page, which is not valid javascript
        self.assertIs(type(data["max_length"]), float)
        page = MovingVolumeModel.babylonjs_script(data, title="moving")
        self.assertNotIn("np.", page)

    def test_debug_page(self):
        page = VolumeModel.babylonjs_script(self.model.babylon_data(), title="model", debug=True)
        self.assertIn("'debug': 1", page)


if __name__ == "__main__":
    unittest.main()
