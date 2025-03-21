"""
Demo usage of Cylinder class.
"""
import design3d
from design3d.core import VolumeModel
from design3d.primitives3d import Cylinder

# 1. Instantiate a red Cylinder directly with the init:
cylinder1 = Cylinder(frame=design3d.OXYZ, radius=0.1, length=0.5, color=(1.0, 0.0, 0.0))

# 2. Instantiate a blue Cylinder with `from_extremal_points` classmethod:
cylinder2 = Cylinder.from_end_points(
    point1=design3d.Point3D(0.5, 0.2, 0.3), point2=design3d.Point3D(0.8, 0.1, 0.1), radius=0.3, color=(0.0, 1.0, 0.0)
)

# 3. Instantiate a green Cylinder with `from_center_point_and_axis` classmethod:
cylinder3 = Cylinder.from_center_point_and_axis(
    center_point=design3d.Point3D(-0.2, -0.3, 0.1), axis=design3d.X3D, radius=0.06, length=0.2, color=(0.0, 0.0, 1.0)
)

# Display the result
volume_model = VolumeModel([cylinder1, cylinder2, cylinder3])
volume_model.babylonjs()
