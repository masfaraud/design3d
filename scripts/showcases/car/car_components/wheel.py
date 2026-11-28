"""
Wheel: tyre, rim, brake disc and caliper.

The wheel frame has its origin at the wheel center and the wheel axis along Y. The wheel is defined for the
left-hand side of the car: its outer side faces -Y.
"""

import design3d as d3d
from design3d.primitives2d import ClosedRoundedLineSegments2D
from design3d.primitives3d import Block, RevolvedProfile
from design3d.wires import ClosedPolygon2D

from .base import Part, SubAssembly

INCH = 0.0254
# Frame whose (u, v) plane is the (Y, Z) plane: profiles are drawn as (axial, radial) coordinates
AXIAL_RADIAL_FRAME = d3d.OYZX


def revolved_around_y(contour, name):
    return RevolvedProfile(AXIAL_RADIAL_FRAME, contour, axis_point=d3d.O3D, axis=d3d.Y3D, name=name)


class Tyre(Part):
    """Tyre from its ISO designation, for instance 225/45 R17."""

    color = (0.12, 0.12, 0.12)

    def __init__(self, width: float, aspect_ratio: float, rim_diameter: float, rim_width: float, name: str = "Tyre"):
        super().__init__(name)
        self.width = width
        self.aspect_ratio = aspect_ratio
        self.rim_diameter = rim_diameter
        self.rim_width = rim_width

    @property
    def diameter(self):
        return self.rim_diameter + 2 * self.aspect_ratio * self.width

    def geometry(self):
        rim_radius = 0.5 * self.rim_diameter
        radius = 0.5 * self.diameter
        sidewall_height = radius - rim_radius
        half_width = 0.5 * self.width
        points = [
            d3d.Point2D(-0.5 * self.rim_width, rim_radius),
            d3d.Point2D(-half_width, rim_radius + 0.35 * sidewall_height),
            d3d.Point2D(-half_width, radius),
            d3d.Point2D(half_width, radius),
            d3d.Point2D(half_width, rim_radius + 0.35 * sidewall_height),
            d3d.Point2D(0.5 * self.rim_width, rim_radius),
        ]
        shoulder_radius = 0.25 * sidewall_height
        contour = ClosedRoundedLineSegments2D(
            points, {1: 0.5 * shoulder_radius, 2: shoulder_radius, 3: shoulder_radius, 4: 0.5 * shoulder_radius}
        )
        return revolved_around_y(contour, self.name)


class Rim(Part):
    """Rim: barrel with flanges and a solid disc, offset towards the outer side."""

    color = (0.75, 0.75, 0.78)

    def __init__(
        self,
        diameter: float,
        width: float,
        hub_bore_diameter: float = 0.065,
        thickness: float = 0.006,
        flange_height: float = 0.015,
        disc_thickness: float = 0.02,
        disc_offset: float = -0.02,
        name: str = "Rim",
    ):
        super().__init__(name)
        self.diameter = diameter
        self.width = width
        self.hub_bore_diameter = hub_bore_diameter
        self.thickness = thickness
        self.flange_height = flange_height
        self.disc_thickness = disc_thickness
        self.disc_offset = disc_offset

    def geometry(self):
        half_width = 0.5 * self.width
        radius = 0.5 * self.diameter
        flange_radius = radius + self.flange_height
        inner_radius = radius - self.thickness
        disc_in = self.disc_offset + 0.5 * self.disc_thickness
        disc_out = self.disc_offset - 0.5 * self.disc_thickness
        hub_radius = 0.5 * self.hub_bore_diameter
        points = [
            (-half_width - self.thickness, flange_radius),
            (-half_width, flange_radius),
            (-half_width, radius),
            (half_width, radius),
            (half_width, flange_radius),
            (half_width + self.thickness, flange_radius),
            (half_width + self.thickness, inner_radius),
            (disc_in, inner_radius),
            (disc_in, hub_radius),
            (disc_out, hub_radius),
            (disc_out, inner_radius),
            (-half_width - self.thickness, inner_radius),
        ]
        contour = ClosedPolygon2D([d3d.Point2D(*point) for point in points])
        return revolved_around_y(contour, self.name)


class BrakeDisc(Part):
    """Brake disc: a hat bolted on the hub and a friction ring on the inner side of the wheel."""

    color = (0.45, 0.45, 0.47)

    def __init__(
        self,
        diameter: float,
        thickness: float,
        ring_width: float = 0.05,
        hat_diameter: float = 0.18,
        ring_axial_position: float = 0.02,
        name: str = "Brake disc",
    ):
        super().__init__(name)
        self.diameter = diameter
        self.thickness = thickness
        self.ring_width = ring_width
        self.hat_diameter = hat_diameter
        self.ring_axial_position = ring_axial_position

    @property
    def ring_mean_radius(self):
        return 0.5 * self.diameter - 0.5 * self.ring_width

    def geometry(self):
        wall = 0.006
        hat_radius = 0.5 * self.hat_diameter
        outer_radius = 0.5 * self.diameter
        inner_radius = outer_radius - self.ring_width
        ring_start = self.ring_axial_position
        ring_end = ring_start + self.thickness
        bore_radius = 0.035
        points = [
            (-0.01, bore_radius),
            (-0.01, hat_radius),
            (ring_start, hat_radius),
            (ring_start, outer_radius),
            (ring_end, outer_radius),
            (ring_end, inner_radius),
            (ring_start + wall, inner_radius),
            (ring_start + wall, hat_radius - wall),
            (-0.01 + wall, hat_radius - wall),
            (-0.01 + wall, bore_radius),
        ]
        contour = ClosedPolygon2D([d3d.Point2D(*point) for point in points])
        return revolved_around_y(contour, self.name)


class BrakeCaliper(Part):
    """Brake caliper straddling the friction ring, behind the wheel center."""

    color = (0.75, 0.1, 0.1)

    def __init__(self, ring_mean_radius: float, disc_thickness: float, ring_axial_center: float, name="Caliper"):
        super().__init__(name)
        self.ring_mean_radius = ring_mean_radius
        self.disc_thickness = disc_thickness
        self.ring_axial_center = ring_axial_center

    def geometry(self):
        # Behind the wheel center (along +X), at the wheel center height
        block_frame = d3d.Frame3D(
            d3d.Point3D(self.ring_mean_radius, self.ring_axial_center, 0),
            0.05 * d3d.X3D,
            (self.disc_thickness + 0.04) * d3d.Y3D,
            0.12 * d3d.Z3D,
        )
        return Block(block_frame, name=self.name)


class Wheel(SubAssembly):
    """Wheel with its brake, built from the tyre designation and the brake disc dimensions."""

    def __init__(
        self,
        tyre_width: float,
        tyre_aspect_ratio: float,
        rim_diameter_inch: float,
        rim_width_inch: float,
        brake_disc_diameter: float,
        brake_disc_thickness: float,
        name: str = "Wheel",
    ):
        super().__init__(name)
        rim_diameter = rim_diameter_inch * INCH
        rim_width = rim_width_inch * INCH
        self.tyre = Tyre(tyre_width, tyre_aspect_ratio, rim_diameter, rim_width, name=f"{name} tyre")
        self.rim = Rim(rim_diameter, rim_width, name=f"{name} rim")
        self.brake_disc = BrakeDisc(brake_disc_diameter, brake_disc_thickness, name=f"{name} brake disc")
        self.caliper = BrakeCaliper(
            self.brake_disc.ring_mean_radius,
            brake_disc_thickness,
            self.brake_disc.ring_axial_position + 0.5 * brake_disc_thickness,
            name=f"{name} caliper",
        )

    @property
    def radius(self):
        return 0.5 * self.tyre.diameter

    def children(self):
        return [(self.tyre, d3d.OXYZ), (self.rim, d3d.OXYZ), (self.brake_disc, d3d.OXYZ), (self.caliper, d3d.OXYZ)]
