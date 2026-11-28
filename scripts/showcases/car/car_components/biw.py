"""
Body in white: floor, sills, rails, pillars, roof, and a transparent body shell showing the silhouette.

The body frame is the car frame: origin on the ground, below the front axle, in the car plane of symmetry.
"""

import math

import design3d as d3d
from design3d.primitives2d import ClosedRoundedLineSegments2D
from design3d.primitives3d import ExtrudedProfile, Loft

from .base import Box, Part, SubAssembly, Tube, frame

STEEL = (0.62, 0.64, 0.68)


def interpolate(x: float, points: list[tuple[float, float]]) -> float:
    """Piecewise linear interpolation of (x, value) points sorted by x."""
    for (x1, value1), (x2, value2) in zip(points, points[1:]):
        if x1 <= x <= x2:
            return value1 + (value2 - value1) * (x - x1) / (x2 - x1)
    raise ValueError(f"{x} is outside of the interpolation range")


class BodyShell(SubAssembly):
    """
    Transparent body shell: the lower body is the side silhouette extruded across the width, with the wheel arches
    cut out, and the greenhouse (windscreen, roof with tumblehome, rear window) is lofted through cross sections.

    :param wheels_x: X of the front and rear axles
    """

    color = (0.15, 0.35, 0.65)
    alpha = 0.18

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        front_overhang: float,
        wheels_x: tuple[float, float],
        wheel_center_height: float,
        arch_radius: float,
        sill_height: float,
        name: str = "Body shell",
    ):
        super().__init__(name)
        x_front = -front_overhang
        x_rear = x_front + length
        front_axle_x, rear_axle_x = wheels_x
        # Side view of the belt line (top of the hood, of the doors and of the tailgate) and of the roof line
        self.belt_line = [
            (x_front, 0.62),
            (x_front + 0.3, 0.8),
            (front_axle_x + 0.55, 0.93),
            (x_rear - 0.1, 0.98),
            (x_rear, 0.86),
        ]
        self.roof_line = [
            (front_axle_x + 0.55, 0.93),
            (front_axle_x + 1.3, height),
            (rear_axle_x - 0.2, height - 0.02),
            (x_rear - 0.1, 0.98),
        ]
        self.lower_body = LowerBody(
            self.belt_line, width, wheels_x, wheel_center_height, arch_radius, sill_height, name="Lower body"
        )
        half_width = 0.5 * width
        # Plan view of the greenhouse: its bottom is inside the lower body, its top narrower (tumblehome)
        top_half_width = [(front_axle_x + 0.55, half_width - 0.12), (front_axle_x + 1.3, half_width - 0.3)]
        top_half_width.append((x_rear, half_width - 0.27))
        # Sections close enough to follow the windscreen and the rear window, the B-spline interpolation of the
        # loft overshooting the roof line by a few millimeters
        stations = [front_axle_x + offset for offset in (0.58, 0.8, 1.05, 1.3, 1.6, 2.0)]
        stations += [rear_axle_x - 0.2, rear_axle_x + 0.125, x_rear - 0.17]
        self.greenhouse = Greenhouse(
            stations, self.belt_line, self.roof_line, half_width - 0.04, top_half_width, name="Greenhouse"
        )

    def children(self):
        return [(self.lower_body, d3d.OXYZ), (self.greenhouse, d3d.OXYZ)]


class LowerBody(Part):
    """Side silhouette below the belt line, extruded across the width, with the wheel arches cut out."""

    color = BodyShell.color
    alpha = BodyShell.alpha

    def __init__(self, belt_line, width, wheels_x, wheel_center_height, arch_radius, sill_height, name="Lower body"):
        super().__init__(name)
        self.belt_line = belt_line
        self.width = width
        self.wheels_x = wheels_x
        self.wheel_center_height = wheel_center_height
        self.arch_radius = arch_radius
        self.sill_height = sill_height

    def arch_points(self, x_center: float, number_points: int = 9):
        """Points of a wheel arch, from rear to front."""
        start = math.asin((self.sill_height - self.wheel_center_height) / self.arch_radius)
        angles = [start + i * (math.pi - 2 * start) / (number_points - 1) for i in range(number_points)]
        return [
            (x_center + self.arch_radius * math.cos(a), self.wheel_center_height + self.arch_radius * math.sin(a))
            for a in angles
        ]

    def geometry(self):
        x_front, x_rear = self.belt_line[0][0], self.belt_line[-1][0]
        front_axle_x, rear_axle_x = self.wheels_x
        # Silhouette drawn clockwise from the bottom of the front bumper, along the belt line
        upper = [(x_front, self.sill_height + 0.05)] + self.belt_line + [(x_rear, self.sill_height + 0.05)]
        lower = (
            [(x_rear - 0.15, self.sill_height)]
            + self.arch_points(rear_axle_x)
            + self.arch_points(front_axle_x)
            + [(x_front + 0.15, self.sill_height)]
        )
        points = [d3d.Point2D(*point) for point in upper + lower]
        radii = {1: 0.1, 2: 0.25, 3: 0.2, 4: 0.08}
        silhouette = ClosedRoundedLineSegments2D(points, radii)
        # Profile in the (X, Z) plane, extruded symmetrically along Y
        shell_frame = d3d.Frame3D(d3d.O3D, d3d.X3D, d3d.Z3D, -d3d.Y3D)
        return ExtrudedProfile(shell_frame, silhouette, [], self.width, symmetric=True, name=self.name)


class Greenhouse(Part):
    """Windscreen, roof and rear window, lofted through cross sections standing on the belt line."""

    color = BodyShell.color
    alpha = BodyShell.alpha

    def __init__(self, stations, belt_line, roof_line, bottom_half_width, top_half_width, name="Greenhouse"):
        super().__init__(name)
        self.stations = stations
        self.belt_line = belt_line
        self.roof_line = roof_line
        self.bottom_half_width = bottom_half_width
        self.top_half_width = top_half_width

    def geometry(self):
        sections, frames = [], []
        for x in self.stations:
            # The bottom overlaps the lower body, so that the end sections keep a height
            bottom = interpolate(x, self.belt_line) - 0.05
            top = interpolate(x, self.roof_line)
            top_width = interpolate(x, self.top_half_width)
            points = [
                d3d.Point2D(-self.bottom_half_width, bottom),
                d3d.Point2D(self.bottom_half_width, bottom),
                d3d.Point2D(top_width, top),
                d3d.Point2D(-top_width, top),
            ]
            sections.append(ClosedRoundedLineSegments2D(points, {0: 0.02, 1: 0.02, 2: 0.03, 3: 0.03}))
            # Sections drawn in the (Y, Z) plane
            frames.append(d3d.Frame3D(d3d.Point3D(x, 0, 0), d3d.Y3D, d3d.Z3D, d3d.X3D))
        return Loft(sections, frames, name=self.name)


class BodyInWhite(SubAssembly):
    """Main body structure, built from the overall dimensions of the car."""

    def __init__(
        self,
        length: float,
        width: float,
        height: float,
        wheelbase: float,
        front_overhang: float,
        ground_clearance: float,
        wheel_radius: float,
        name: str = "Body in white",
    ):
        super().__init__(name)
        self.length = length
        self.width = width
        self.height = height
        self.wheelbase = wheelbase
        self.front_overhang = front_overhang
        self.ground_clearance = ground_clearance

        x_front = -front_overhang
        x_rear = x_front + length
        self.floor_height = ground_clearance + 0.05
        sill_height = ground_clearance + 0.02
        half_width = 0.5 * width - 0.04
        roof_height = height - 0.03
        roof_half_width = half_width - 0.13

        # Symmetric parts: a single instance placed on both sides
        self.sill_length = wheelbase - 2 * (wheel_radius + 0.08)
        self.sill = Box.centered(self.sill_length, 0.12, 0.16, color=STEEL, name="Sill")
        self.sill_y = half_width - 0.06
        self.sill_z = sill_height + 0.08
        self.front_rail = Box.centered(front_overhang + 0.55, 0.07, 0.11, color=STEEL, name="Front rail")
        self.front_rail_y = 0.45

        self.floor = Box(
            (0.35, -half_width + 0.1, self.floor_height),
            (wheelbase + 0.35, half_width - 0.1, self.floor_height + 0.01),
            color=STEEL,
            name="Floor",
        )
        self.firewall = Box(
            (0.3, -half_width + 0.1, self.floor_height), (0.34, half_width - 0.1, 0.85), color=STEEL, name="Firewall"
        )
        self.front_bumper_beam = Box(
            (x_front + 0.05, -0.55, 0.38), (x_front + 0.15, 0.55, 0.5), color=STEEL, name="Front bumper beam"
        )
        self.rear_bumper_beam = Box(
            (x_rear - 0.15, -0.55, 0.45), (x_rear - 0.05, 0.55, 0.55), color=STEEL, name="Rear bumper beam"
        )
        self.roof = Box(
            (1.35, -roof_half_width, roof_height - 0.01),
            (wheelbase - 0.25, roof_half_width, roof_height),
            color=STEEL,
            name="Roof panel",
        )

        # Side dependent parts: one instance per side
        self.side_tubes = []
        for side, side_name in ((-1, "Left"), (1, "Right")):
            points = {
                "cowl": (0.55, side * (half_width - 0.05), 0.9),
                "roof_front": (1.35, side * roof_half_width, roof_height),
                "b_bottom": (1.75, side * self.sill_y, self.sill_z),
                "b_top": (1.65, side * roof_half_width, roof_height),
                "roof_rear": (wheelbase - 0.25, side * roof_half_width, roof_height),
                "c_bottom": (x_rear - 0.15, side * (half_width - 0.05), 0.95),
            }
            for start, end, label in (
                ("cowl", "roof_front", "A pillar"),
                ("b_bottom", "b_top", "B pillar"),
                ("roof_rear", "c_bottom", "C pillar"),
                ("roof_front", "roof_rear", "roof rail"),
            ):
                self.side_tubes.append(Tube(points[start], points[end], 0.06, color=STEEL, name=f"{side_name} {label}"))

        self.shell = BodyShell(
            length,
            width,
            height,
            front_overhang,
            (0.0, wheelbase),
            wheel_radius,
            wheel_radius + 0.05,
            sill_height,
        )

    def children(self):
        sill_x = 0.5 * self.wheelbase
        rail_x = 0.5 * (-self.front_overhang + 0.55)
        children = []
        for side in (-1, 1):
            children.append((self.sill, frame(sill_x, side * self.sill_y, self.sill_z)))
            children.append((self.front_rail, frame(rail_x, side * self.front_rail_y, 0.42)))
        children.extend(
            (part, d3d.OXYZ)
            for part in [self.floor, self.firewall, self.front_bumper_beam, self.rear_bumper_beam, self.roof]
        )
        children.extend((tube, d3d.OXYZ) for tube in self.side_tubes)
        children.append((self.shell, d3d.OXYZ))
        return children
