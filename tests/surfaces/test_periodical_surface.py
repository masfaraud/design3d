import unittest
import os

import design3d
import design3d.wires as d3dw
import design3d.edges as d3de
from design3d import surfaces

folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'objects_periodical_surface')


class TestPeriodicalSurface(unittest.TestCase):

    def test_bsplinecurve3d_to_2d(self):
        surface = surfaces.CylindricalSurface3D.from_json(os.path.join(folder, "periodicalsurface_with_theta_discontinuity.json"))
        bspline = d3de.BSplineCurve3D.from_json(os.path.join(folder, "bsplinecurve_with_theta_discontinuity.json"))
        bspline2d = surface.bsplinecurve3d_to_2d(bspline)[0]
        theta1 = bspline2d.start.x
        theta2 = bspline2d.end.x
        self.assertEqual(theta1,  0.9979944870045463)
        self.assertEqual(theta2, design3d.TWO_PI)


if __name__ == '__main__':
    unittest.main()
