"""
Front-wheel drive drivetrain: gearbox with its differential, and two driveshafts of different lengths.

The drivetrain frame has its origin on the front axle, at the wheel center height, in the car plane of symmetry.
"""

import math

import design3d as d3d
from design3d.primitives2d import CirclesConvexHull2D
from design3d.primitives3d import Cylinder, ExtrudedProfile

from .base import Part, SubAssembly, frame, frame_along

STEEL = (0.35, 0.35, 0.37)


class Gearbox(Part):
    """
    Transverse gearbox housing enveloping the clutch bell and the differential.

    Its frame has its origin on the crankshaft axis, on the engine mounting face, and it extends along -Y.
    """

    color = (0.6, 0.62, 0.65)

    def __init__(self, length: float, differential_position: tuple[float, float], name: str = "Gearbox"):
        super().__init__(name)
        self.length = length
        self.differential_position = differential_position

    def geometry(self):
        diff_x, diff_z = self.differential_position
        profile = CirclesConvexHull2D([d3d.O2D, d3d.Point2D(diff_x, diff_z)], [0.15, 0.11])
        housing_frame = d3d.Frame3D(d3d.O3D, d3d.X3D, d3d.Z3D, -d3d.Y3D)
        # Cast housing, demolded away from the engine mounting face
        return ExtrudedProfile(housing_frame, profile, [], self.length, draft_angle=math.radians(3), name=self.name)


class CVJoint(Part):
    """Constant velocity joint housing along Z, centered at the origin."""

    color = (0.1, 0.1, 0.1)

    def __init__(self, diameter: float = 0.09, length: float = 0.09, name: str = "CV joint"):
        super().__init__(name)
        self.diameter = diameter
        self.length = length

    def geometry(self):
        return Cylinder(d3d.OXYZ, 0.5 * self.diameter, self.length, name=self.name)


class Shaft(Part):
    """Plain shaft along Z, from z=0 to z=length."""

    color = STEEL

    def __init__(self, diameter: float, length: float, name: str = "Shaft"):
        super().__init__(name)
        self.diameter = diameter
        self.length = length

    def geometry(self):
        return Cylinder(frame(z=0.5 * self.length), 0.5 * self.diameter, self.length, name=self.name)


class Driveshaft(SubAssembly):
    """Driveshaft along Z between two CV joints, the joint instance is shared by all the driveshafts."""

    def __init__(self, length: float, joint: CVJoint, name: str = "Driveshaft"):
        super().__init__(name)
        self.length = length
        self.joint = joint
        self.shaft = Shaft(0.026, length, name=f"{name} shaft")

    def children(self):
        return [(self.shaft, d3d.OXYZ), (self.joint, d3d.OXYZ), (self.joint, frame(z=self.length))]


class Drivetrain(SubAssembly):
    """
    Gearbox bolted on the engine and driveshafts from the differential to the wheel hubs.

    :param crank_position: (x, z) of the crankshaft axis in the drivetrain frame
    :param flange_y: Y of the engine mounting face, the gearbox extends towards -Y
    :param hub_y: Y of the outer joints, on each side of the car
    """

    def __init__(self, crank_position, flange_y: float, hub_y: float, gearbox_length: float = 0.36, name="Drivetrain"):
        super().__init__(name)
        self.crank_position = crank_position
        self.flange_y = flange_y
        crank_x, crank_z = crank_position
        # The differential is on the wheels axis
        self.gearbox = Gearbox(gearbox_length, (-crank_x, -crank_z))
        differential_y = flange_y - 0.55 * gearbox_length
        self.joint = CVJoint()
        self.left_inner = d3d.Point3D(0, flange_y - gearbox_length - 0.03, 0)
        self.right_inner = d3d.Point3D(0, differential_y + 0.2, 0)
        self.left_outer = d3d.Point3D(0, -hub_y, 0)
        self.right_outer = d3d.Point3D(0, hub_y, 0)
        self.left_driveshaft = Driveshaft(
            self.left_inner.point_distance(self.left_outer), self.joint, name="Left driveshaft"
        )
        self.right_driveshaft = Driveshaft(
            self.right_inner.point_distance(self.right_outer), self.joint, name="Right driveshaft"
        )

    def children(self):
        crank_x, crank_z = self.crank_position
        return [
            (self.gearbox, frame(crank_x, self.flange_y, crank_z)),
            (self.left_driveshaft, frame_along(self.left_inner, self.left_outer)),
            (self.right_driveshaft, frame_along(self.right_inner, self.right_outer)),
        ]
