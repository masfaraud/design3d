"""
Test for method Cylinder.point_belongs and Cylinder.random_point_inside
"""

import design3d
from design3d.primitives3d import Cylinder

cylinder = Cylinder.from_center_point_and_axis(center_point=design3d.O3D, axis=design3d.Z3D, radius=0.02, length=0.1)

p = cylinder.random_point_inside()

if not cylinder.point_belongs(p):
    raise ValueError("Point should belong to cylinder")
