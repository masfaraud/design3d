"""
Rack and pinion steering, with the column and the steering wheel on the driver side.

The steering frame has its origin on the front axle, at the wheel center height, in the car plane of symmetry.
"""

import design3d as d3d
from design3d.curves import Circle2D
from design3d.primitives3d import Cylinder, RevolvedProfile
from design3d.wires import Contour2D

from .base import Part, SubAssembly, Tube, frame, frame_along

DARK = (0.12, 0.12, 0.12)


class RackHousing(Part):
    """Rack housing along Y, centered at the origin."""

    color = (0.5, 0.5, 0.52)

    def __init__(self, length: float, diameter: float = 0.05, name: str = "Rack housing"):
        super().__init__(name)
        self.length = length
        self.diameter = diameter

    def geometry(self):
        return Cylinder(
            d3d.Frame3D(d3d.O3D, d3d.Z3D, d3d.X3D, d3d.Y3D), 0.5 * self.diameter, self.length, name=self.name
        )


class SteeringWheelRim(Part):
    """Torus of the steering wheel, around Z."""

    color = DARK

    def __init__(self, diameter: float, grip_diameter: float = 0.03, name: str = "Steering wheel rim"):
        super().__init__(name)
        self.diameter = diameter
        self.grip_diameter = grip_diameter

    def geometry(self):
        grip = Contour2D.from_circle(
            Circle2D.from_center_and_radius(d3d.Point2D(0.5 * self.diameter, 0), 0.5 * self.grip_diameter)
        )
        # Profile drawn in the (X, Z) plane, revolved around Z
        profile_frame = d3d.Frame3D(d3d.O3D, d3d.X3D, d3d.Z3D, -d3d.Y3D)
        return RevolvedProfile(profile_frame, grip, axis_point=d3d.O3D, axis=d3d.Z3D, name=self.name)


class SteeringWheel(SubAssembly):
    """Steering wheel along Z: hub and rim."""

    def __init__(self, diameter: float, name: str = "Steering wheel"):
        super().__init__(name)
        self.rim = SteeringWheelRim(diameter)
        self.hub = Tube((0, 0, -0.08), (0, 0, 0.02), 0.15, color=DARK, name="Steering wheel hub")

    def children(self):
        return [(self.rim, d3d.OXYZ), (self.hub, d3d.OXYZ)]


class Steering(SubAssembly):
    """
    Rack behind the wheels axis, tie rods to the knuckles and a column up to the steering wheel.

    :param steering_wheel_center: Position of the steering wheel center in the steering frame
    """

    def __init__(self, track: float, steering_wheel_center: tuple, rack_position=(0.15, 0.05), name="Steering"):
        super().__init__(name)
        rack_x, rack_z = rack_position
        rack_length = track - 0.6
        self.rack_position = rack_position
        self.rack = RackHousing(rack_length)
        self.tie_rods = []
        for side, side_name in ((-1, "Left"), (1, "Right")):
            rack_end = (rack_x, side * 0.5 * rack_length, rack_z)
            knuckle_arm = (0.13, side * (0.5 * track - 0.16), 0.0)
            self.tie_rods.append(Tube(rack_end, knuckle_arm, 0.016, color=DARK, name=f"{side_name} tie rod"))
        # The pinion is on the driver side
        driver_side = 1 if steering_wheel_center[1] > 0 else -1
        pinion = (rack_x, driver_side * 0.25 * rack_length, rack_z + 0.03)
        self.column = Tube(pinion, steering_wheel_center, 0.03, color=DARK, name="Steering column")
        self.steering_wheel = SteeringWheel(0.37)

    def children(self):
        wheel_frame = frame_along(self.column.point2, self.column.point2 + (self.column.point2 - self.column.point1))
        rack_x, rack_z = self.rack_position
        return (
            [(self.rack, frame(rack_x, 0, rack_z))]
            + [(tie_rod, d3d.OXYZ) for tie_rod in self.tie_rods]
            + [(self.column, d3d.OXYZ), (self.steering_wheel, wheel_frame)]
        )
