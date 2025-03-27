"""
Unittest for ClosedPolygon2D class
"""
import unittest
import math
import random

import design3d
import design3d.core as d3dc
import design3d.display as d3dd
import design3d.wires as d3dw
import design3d.faces as d3df

random.seed(781)

class TestClosedPolygon3D(unittest.TestCase):
    
    def circular_polygon(self, mean_radius:float, delta_radius, expected_number_points:int,
                         x:design3d.Vector3D, y:design3d.Vector3D, theta0:float=0.):
        """
        Create a polygon around a circular pattern
        """
        theta = theta0
        points = []
        theta_r = design3d.TWO_PI / expected_number_points
        theta_end = theta0 + design3d.TWO_PI
        z = x.cross(y)
        initial_point = x.to_point()
        while theta < theta_end:
            radius = mean_radius + 2*(random.random() - 0.5)*delta_radius
            points.append((radius * initial_point).rotation(design3d.O3D, z, theta))
            theta += theta_r + (random.random() - 0.5)*theta_r
        return d3dw.ClosedPolygon3D(points)

    def test_sewing(self):
        z1 = 0.1
        z2 = 0.18

        polygon1 = self.circular_polygon(0.15, 0.07, 12, design3d.X3D, design3d.Y3D)
        polygon1 = polygon1.translation(z1*design3d.Z3D)

        polygon2 = self.circular_polygon(0.17, 0.03, 25, design3d.X3D, design3d.Y3D)
        polygon2 = polygon2.translation(z2*design3d.Z3D)

        ax = polygon1.plot()
        polygon2.plot(ax=ax, edge_style=d3dc.EdgeStyle(color='r'))

        sewing_triangles = polygon1.sewing(polygon2, design3d.X3D, design3d.Y3D)
        poly1_normal_out = 0.
        poly2_normal_out = 0.

        for p1, p2, p3 in sewing_triangles:
            triangle = d3df.Triangle3D(p1, p2, p3)
            triangle_normal = triangle.normal()
            triangle_middle = triangle.middle()
            if ((p1 in polygon1.points) + (p2 in polygon1.points) + (p3 in polygon1.points)) == 2:
                # based on polygon1
                poly1_normal_out += triangle_normal.dot(triangle_middle)
            else:
                poly2_normal_out += triangle_normal.dot(triangle_middle)
            triangle.plot(ax=ax)
            plot_normal = 0.05*triangle_normal
            plot_normal.plot(ax=ax, starting_point=triangle_middle)

        # If normals are in different directions, the test fails
        self.assertGreater(poly1_normal_out/poly2_normal_out, 0.)

        # Normals should point on the outside
        self.assertGreater(poly1_normal_out, 0.)
        self.assertGreater(poly2_normal_out, 0.)


if __name__ == '__main__':
    unittest.main()
