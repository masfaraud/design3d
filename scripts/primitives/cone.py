"""
Demo usage of Cone class.
"""
import math

import design3d
from design3d.core import VolumeModel
from design3d.primitives3d import Cone

# 1. Instantiate a red Cone directly with the init:
cone1 = Cone(frame=design3d.OXYZ, radius=0.1, length=0.5, color=(1.0, 0.0, 0.0))

# 2. Instantiate a green Cone with `from_center_point_and_axis` classmethod:
cone2 = Cone.from_center_point_and_axis(
    center_point=design3d.Point3D(-0.2, -0.3, 0.1), axis=design3d.X3D, radius=0.06, length=0.2, color=(0.0, 1.0, 0.0)
)

# 3. Instantiate a blue Cone from moving the green cone:
cone3 = cone2.translation(design3d.Vector3D(0.2, 0.1, -0.3))
cone3 = cone3.rotation(design3d.O3D, design3d.Z3D, math.pi / 2)
cone3.color = (0.0, 0.0, 1.0)

# Display the result
volume_model = VolumeModel([cone1, cone2, cone3])
volume_model.babylonjs()
