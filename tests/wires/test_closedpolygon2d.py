"""
Unittest for ClosedPolygon2D class
"""
import unittest
import numpy as np
import design3d
import design3d.display as d3dd
import design3d.wires as d3dw


class TestClosedPolygon2D(unittest.TestCase):
    # Create a ClosedPolygon2D object with a list of points
    points = [design3d.Point2D(0, 0), design3d.Point2D(1, 0), design3d.Point2D(1, 1), design3d.Point2D(0, 1)]
    polygon = d3dw.ClosedPolygon2D(points)
    def test_triangulation(self):


        # Call the triangulation method with different options
        mesh1 = self.polygon.triangulation()
        mesh2 = self.polygon.triangulation('p')
        mesh3 = self.polygon.triangulation('pa0.25')  # No triangles with area greter than 0.25

        # Assert that the returned object is a d3dd.DisplayMesh2D
        self.assertIsInstance(mesh1, d3dd.Mesh2D)
        self.assertIsInstance(mesh2, d3dd.Mesh2D)
        self.assertIsInstance(mesh3, d3dd.Mesh2D)

        # Assert that the mesh has the correct number of points and triangles
        self.assertEqual(len(mesh1.vertices), 4)
        self.assertEqual(len(mesh1.triangles), 2)
        self.assertEqual(len(mesh2.vertices), 4)
        self.assertEqual(len(mesh2.triangles), 2)
        self.assertEqual(len(mesh3.vertices), 5)
        self.assertEqual(len(mesh3.triangles), 4)

    def test_point_belongs(self):
        # create a star-shaped polygon with 5 points
        polygon = d3dw.ClosedPolygon2D([design3d.Point2D(0, 0), design3d.Point2D(1, 2), design3d.Point2D(3, 0),
                                       design3d.Point2D(2, -2), design3d.Point2D(0, -1)])

        # test points inside the polygon
        points_inside = [design3d.Point2D(1, 1), design3d.Point2D(1.5, 0), design3d.Point2D(2, -1)]
        for point in points_inside:
            self.assertTrue(polygon.point_inside(point))
            self.assertTrue(polygon.point_inside(point, include_edge_points=True))

        # test points on the edge of the polygon
        edge_points = [design3d.Point2D(0, 0), design3d.Point2D(0.5, 1),
                       design3d.Point2D(1, 2), design3d.Point2D(2, 1), design3d.Point2D(3, 0),
                       design3d.Point2D(2.5, -1), design3d.Point2D(2, -2), design3d.Point2D(1, -1.5),
                       design3d.Point2D(0, -1), design3d.Point2D(0, -0.5)]
        for point in edge_points:
            self.assertFalse(polygon.point_inside(point))
            self.assertTrue(polygon.point_inside(point, include_edge_points=True))

        # test a point outside the polygon
        point = design3d.Point2D(4, 0)
        self.assertFalse(polygon.point_inside(point))
        self.assertFalse(polygon.point_inside(point, include_edge_points=True))
        polygon = d3dw.ClosedPolygon2D([design3d.Point2D(0.025066533673536538, 0.0257663365438965),
                                       design3d.Point2D(0.02895747485348258, 0.026481373525337516),
                                       design3d.Point2D(0.03197047286753098, 0.03014226404424863),
                                       design3d.Point2D(0.031092529701331955, 0.03308811758234674),
                                       design3d.Point2D(0.027201595008037212, 0.03237308848256351),
                                       design3d.Point2D(0.0241885905068443, 0.028712190081863796)])
        point = design3d.Point2D(0.027822689953649605, 0.02627283447706946)
        self.assertTrue(polygon.point_inside(point, True))
        self.assertFalse(polygon.point_inside(point, False))

    def test_points_in_polygon(self):
        x = np.linspace(0, 1, num=12, dtype=np.float64)
        y = np.linspace(0, 1, num=4, dtype=np.float64)
        # Generate all points in the grid
        grid_points = np.array([[xi, yi] for xi in x for yi in y], dtype=np.float64)
        test = self.polygon.points_in_polygon(grid_points, include_edge_points=True)
        for value in test:
            self.assertTrue(value)


if __name__ == '__main__':
    unittest.main()
