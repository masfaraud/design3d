"""
Interior and underbody equipment: seats, fuel tank and exhaust line.

The frames are the car frame unless stated otherwise.
"""

import math

import design3d as d3d
from design3d.curves import Circle2D
from design3d.primitives3d import Cylinder, OpenRoundedLineSegments3D, Sweep
from design3d.wires import Contour2D

from .base import Box, Part, SubAssembly, frame

FABRIC = (0.2, 0.2, 0.22)


class Seat(SubAssembly):
    """
    Seat with its origin at the H-point (hip joint of the seated occupant): cushion forward, reclined backrest behind.
    """

    cushion_length = 0.45
    cushion_thickness = 0.12
    backrest_thickness = 0.1
    backrest_height = 0.6
    # Position of the bottom of the backrest center line relative to the H-point: behind it and below it
    backrest_base = (0.15, -0.05)

    def __init__(self, width: float, recline_angle: float = math.radians(20), name: str = "Seat"):
        super().__init__(name)
        self.width = width
        self.recline_angle = recline_angle
        self.cushion = Box(
            (-self.cushion_length, -0.5 * width, -0.03 - self.cushion_thickness),
            (0.05, 0.5 * width, -0.03),
            color=FABRIC,
            name=f"{name} cushion",
        )
        self.backrest = Box.centered(
            self.backrest_thickness, width, self.backrest_height, color=FABRIC, name=f"{name} backrest"
        )
        self.headrest = Box.centered(0.08, min(width, 0.26), 0.18, color=FABRIC, name=f"{name} headrest")

    def backrest_rear_x(self, z: float) -> float:
        """X of the rear face of the backrest at the height z, in the seat frame."""
        cos, sin = math.cos(self.recline_angle), math.sin(self.recline_angle)
        base_x, base_z = self.backrest_base
        half_thickness = 0.5 * self.backrest_thickness
        # Point of the rear face: base + half_thickness * u + h * w, with u = (cos, -sin) and w = (sin, cos)
        h = (z - base_z + half_thickness * sin) / cos
        return base_x + half_thickness * cos + h * sin

    def children(self):
        # The backrest is tilted rearwards (towards +X) around Y
        cos, sin = math.cos(self.recline_angle), math.sin(self.recline_angle)
        u = d3d.Vector3D(cos, 0, -sin)
        w = d3d.Vector3D(sin, 0, cos)
        base_x, base_z = self.backrest_base

        def reclined(height):
            return d3d.Frame3D(d3d.Point3D(base_x + height * sin, 0, base_z + height * cos), u, d3d.Y3D, w)

        half_height = 0.5 * self.backrest_height
        return [
            (self.cushion, d3d.OXYZ),
            (self.backrest, reclined(half_height)),
            (self.headrest, reclined(self.backrest_height + 0.1)),
        ]


class ExhaustPipe(Part):
    """Exhaust pipe from the engine down under the floor to the rear of the car."""

    color = (0.55, 0.5, 0.45)

    def __init__(self, points: list[tuple], diameter: float = 0.05, name: str = "Exhaust pipe"):
        super().__init__(name)
        self.points = points
        self.diameter = diameter

    def geometry(self):
        wire = OpenRoundedLineSegments3D(
            [d3d.Point3D(*point) for point in self.points], {i: 0.12 for i in range(1, len(self.points) - 1)}
        )
        section = Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.O2D, 0.5 * self.diameter))
        return Sweep(section, wire, name=self.name)


class Muffler(Part):
    """Rear muffler, along Y, centered at the origin."""

    color = (0.4, 0.38, 0.36)

    def __init__(self, diameter: float, length: float, name: str = "Muffler"):
        super().__init__(name)
        self.diameter = diameter
        self.length = length

    def geometry(self):
        return Cylinder(
            d3d.Frame3D(d3d.O3D, d3d.Z3D, d3d.X3D, d3d.Y3D), 0.5 * self.diameter, self.length, name=self.name
        )


class Exhaust(SubAssembly):
    """Exhaust line from the engine front face to a transverse muffler behind the rear axle."""

    def __init__(self, engine_outlet: tuple, muffler_x: float, floor_height: float, name: str = "Exhaust"):
        super().__init__(name)
        x0, y0, z0 = engine_outlet
        under_floor = floor_height - 0.07
        self.muffler_position = (muffler_x, 0.0, under_floor + 0.05)
        points = [
            (x0, y0, z0),
            (x0 - 0.11, y0, z0 - 0.1),
            (x0 - 0.09, y0, under_floor),
            (x0 + 0.6, 0.0, under_floor),
            (muffler_x - 0.4, 0.0, under_floor),
            (muffler_x - 0.1, 0.0, under_floor + 0.05),
            (muffler_x, 0.0, under_floor + 0.05),
        ]
        self.pipe = ExhaustPipe(points)
        self.muffler = Muffler(0.18, 0.6)

    def children(self):
        return [(self.pipe, d3d.OXYZ), (self.muffler, frame(*self.muffler_position))]
