#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""


import design3d as d3d
import design3d.faces as faces
from design3d import surfaces

R = 0.32
alpha = 0.2
cs = surfaces.ConicalSurface3D(d3d.Frame3D(
                        d3d.Point3D.random(-0.1, 0.1, -0.1, 0.2, -0.2, 0.1),
                        d3d.X3D, d3d.Y3D, d3d.Z3D), alpha)

cf = faces.ConicalFace3D.from_surface_rectangular_cut(cs, -0.01, 1.3, 0., 0.3)

cf.surface2d.plot()
cf.babylonjs(debug=True, use_cdn=False)
