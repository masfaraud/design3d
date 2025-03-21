"""
Demo usage of HollowCylinder class.
"""
import design3d
from design3d.core import VolumeModel
from design3d.primitives3d import HollowCylinder

# 1. Instantiate a red HollowCylinder directly with the init:
hollow_cylinder1 = HollowCylinder(frame=design3d.OXYZ, inner_radius=0.08, outer_radius=0.1, length=0.5, color=(1.0, 0.0, 0.0))

# 2. Instantiate a blue HollowCylinder with `from_end_points` classmethod:
hollow_cylinder2 = HollowCylinder.from_end_points(
    point1=design3d.Point3D(0.5, 0.2, 0.3),
    point2=design3d.Point3D(0.8, 0.1, 0.1),
    inner_radius=0.2,
    outer_radius=0.3,
    color=(0.0, 1.0, 0.0),
)

# 3. Instantiate a green HollowCylinder with `from_center_point_and_axis` classmethod:
hollow_cylinder3 = HollowCylinder.from_center_point_and_axis(
    center_point=design3d.Point3D(-0.2, -0.3, 0.1),
    axis=design3d.X3D,
    inner_radius=0.03,
    outer_radius=0.06,
    length=0.2,
    color=(0.0, 0.0, 1.0),
)

# Display the result
volume_model = VolumeModel([hollow_cylinder1, hollow_cylinder2, hollow_cylinder3])
volume_model.babylonjs()
