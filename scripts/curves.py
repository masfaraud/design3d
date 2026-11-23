"""
Some Volmdlr models for curves.

"""

import design3d
from design3d import curves

vector1 = design3d.Vector3D(1, 1, 1)
vector1 = vector1.unit_vector()
vector2 = vector1.deterministic_unit_normal_vector()
vector3 = vector1.cross(vector2)
frame = design3d.Frame3D(design3d.O3D, vector1, vector2, vector3)

circle3d = curves.Circle3D(frame, 1)
