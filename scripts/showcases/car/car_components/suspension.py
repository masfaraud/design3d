"""
Suspensions: MacPherson struts at the front, a torsion beam at the rear.

The frame of each suspension has its origin on the axle, at the wheel center height, in the car plane of symmetry.
Side is -1 for the left-hand side (Y < 0) and +1 for the right-hand side.
"""

import math

import design3d as d3d
from design3d.curves import Circle2D
from design3d.edges import BSplineCurve3D
from design3d.primitives2d import CirclesConvexHull2D
from design3d.primitives3d import Block, Cylinder, ExtrudedProfile, HollowCylinder, OpenRoundedLineSegments3D, Sweep
from design3d.wires import Contour2D, Wire3D

from .base import Part, SubAssembly, frame, frame_along

STEEL = (0.3, 0.3, 0.32)
SPRING_COLOR = (0.9, 0.75, 0.1)


def circle_contour(radius: float) -> Contour2D:
    return Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.O2D, radius))


class CoilSpring(Part):
    """Helical spring along Z, from z=0 to z=length."""

    color = SPRING_COLOR

    def __init__(self, mean_diameter: float, wire_diameter: float, length: float, turns: float, name="Spring"):
        super().__init__(name)
        self.mean_diameter = mean_diameter
        self.wire_diameter = wire_diameter
        self.length = length
        self.turns = turns

    def geometry(self):
        radius = 0.5 * self.mean_diameter
        number_points = int(8 * self.turns) + 1
        points = []
        for i in range(number_points):
            ratio = i / (number_points - 1)
            angle = 2 * math.pi * self.turns * ratio
            points.append(d3d.Point3D(radius * math.cos(angle), radius * math.sin(angle), self.length * ratio))
        helix = BSplineCurve3D.from_points_interpolation(points, 3)
        return Sweep(circle_contour(0.5 * self.wire_diameter), Wire3D([helix]), name=self.name)


class Damper(Part):
    """Damper body along Z, from z=0 to z=length."""

    color = STEEL

    def __init__(self, diameter: float, length: float, name: str = "Damper"):
        super().__init__(name)
        self.diameter = diameter
        self.length = length

    def geometry(self):
        return Cylinder(frame(z=0.5 * self.length), 0.5 * self.diameter, self.length, name=self.name)


class SpringSeat(Part):
    """Cup holding a spring end, centered at the origin, axis along Z."""

    color = STEEL

    def __init__(self, inner_diameter: float, outer_diameter: float, thickness: float = 0.006, name="Spring seat"):
        super().__init__(name)
        self.inner_diameter = inner_diameter
        self.outer_diameter = outer_diameter
        self.thickness = thickness

    def geometry(self):
        return HollowCylinder(
            d3d.OXYZ, 0.5 * self.inner_diameter, 0.5 * self.outer_diameter, self.thickness, name=self.name
        )


class Strut(SubAssembly):
    """MacPherson strut along Z: damper, rod, spring between two identical seats."""

    def __init__(self, length: float, spring_mean_diameter: float, name: str = "Strut"):
        super().__init__(name)
        self.length = length
        self.body_length = 0.55 * length
        self.spring_start = 0.4 * length
        self.spring_end = length - 0.03
        self.body = Damper(0.05, self.body_length, name="Strut body")
        self.rod = Damper(0.022, length - self.body_length, name="Strut rod")
        self.spring = CoilSpring(
            spring_mean_diameter, 0.012, self.spring_end - self.spring_start, turns=5.5, name="Front spring"
        )
        self.seat = SpringSeat(0.05, spring_mean_diameter + 0.025, name="Front spring seat")

    def children(self):
        return [
            (self.body, d3d.OXYZ),
            (self.rod, frame(z=self.body_length)),
            (self.spring, frame(z=self.spring_start)),
            (self.seat, frame(z=self.spring_start)),
            (self.seat, frame(z=self.spring_end)),
        ]


class Knuckle(Part):
    """Steering knuckle, inboard of the wheel center."""

    color = (0.35, 0.35, 0.35)

    def __init__(self, side: int, name: str = "Knuckle"):
        super().__init__(name)
        self.side = side

    def geometry(self):
        return Block(frame(0, -self.side * 0.09, 0, 0.09 * d3d.X3D, 0.05 * d3d.Y3D, 0.22 * d3d.Z3D), name=self.name)


class LowerArm(Part):
    """Triangular lower control arm: a ball joint under the knuckle and two pivots on the subframe."""

    color = STEEL

    def __init__(self, side: int, inner_offset: float, name: str = "Lower arm"):
        super().__init__(name)
        self.side = side
        self.inner_offset = inner_offset

    def geometry(self):
        y_ball = -self.side * 0.11
        y_pivots = -self.side * self.inner_offset
        profile = CirclesConvexHull2D(
            [d3d.Point2D(0, y_ball), d3d.Point2D(-0.08, y_pivots), d3d.Point2D(0.28, y_pivots)], [0.03, 0.025, 0.035]
        )
        return ExtrudedProfile(frame(z=-0.12), profile, [], 0.02, symmetric=True, name=self.name)


class MacPhersonCorner(SubAssembly):
    """Corner of the front axle, with its origin at the wheel center."""

    def __init__(self, side: int, strut: Strut, strut_bottom_offset: float, strut_top_offset: float, arm_inner_offset):
        super().__init__("Front left corner" if side < 0 else "Front right corner")
        self.side = side
        self.strut = strut
        self.strut_bottom = d3d.Point3D(0, -side * strut_bottom_offset, 0.05)
        top_offset = math.sqrt(strut.length**2 - (strut_top_offset - strut_bottom_offset) ** 2)
        self.strut_top = d3d.Point3D(0, -side * strut_top_offset, 0.05 + top_offset)
        side_name = "Left" if side < 0 else "Right"
        self.knuckle = Knuckle(side, name=f"{side_name} knuckle")
        self.lower_arm = LowerArm(side, arm_inner_offset, name=f"{side_name} lower arm")

    def children(self):
        return [
            (self.knuckle, d3d.OXYZ),
            (self.lower_arm, d3d.OXYZ),
            (self.strut, frame_along(self.strut_bottom, self.strut_top)),
        ]


class AntiRollBar(Part):
    """Anti-roll bar behind the wheels axis, linked to the struts."""

    color = (0.1, 0.1, 0.1)

    def __init__(self, width: float, diameter: float = 0.022, name: str = "Anti-roll bar"):
        super().__init__(name)
        self.width = width
        self.diameter = diameter

    def geometry(self):
        half_width = 0.5 * self.width
        # Behind the gearbox, above the subframe
        points = [
            d3d.Point3D(0.05, -half_width, 0.0),
            d3d.Point3D(0.25, -half_width + 0.1, -0.1),
            d3d.Point3D(0.25, half_width - 0.1, -0.1),
            d3d.Point3D(0.05, half_width, 0.0),
        ]
        wire = OpenRoundedLineSegments3D(points, {1: 0.06, 2: 0.06})
        return Sweep(circle_contour(0.5 * self.diameter), wire, name=self.name)


class Subframe(Part):
    """Front cradle carrying the lower arms."""

    color = (0.2, 0.2, 0.22)

    def __init__(self, width: float, name: str = "Subframe"):
        super().__init__(name)
        self.width = width

    def geometry(self):
        return Block(frame(0.12, 0, -0.14, 0.45 * d3d.X3D, self.width * d3d.Y3D, 0.05 * d3d.Z3D), name=self.name)


class FrontSuspension(SubAssembly):
    """MacPherson front axle: the same strut is used on both sides, tilted inwards."""

    def __init__(self, track: float, name: str = "Front suspension"):
        super().__init__(name)
        self.track = track
        strut = Strut(length=0.56, spring_mean_diameter=0.13)
        arm_inner_offset = 0.5 * track - 0.38
        self.corners = [MacPhersonCorner(side, strut, 0.15, 0.24, arm_inner_offset) for side in (-1, 1)]
        self.subframe = Subframe(2 * arm_inner_offset + 0.1)
        self.anti_roll_bar = AntiRollBar(track - 0.45)

    def children(self):
        corners = [(corner, frame(y=corner.side * 0.5 * self.track)) for corner in self.corners]
        return corners + [(self.subframe, d3d.OXYZ), (self.anti_roll_bar, d3d.OXYZ)]


class TorsionBeam(Part):
    """V-section cross beam linking the trailing arms, ahead of the rear axle."""

    color = STEEL

    def __init__(self, length: float, name: str = "Torsion beam"):
        super().__init__(name)
        self.length = length

    def geometry(self):
        # Section in the (X, Z) plane, extruded along -Y from y = length / 2
        points = [(-0.06, 0.05), (0.0, -0.05), (0.06, 0.05), (0.05, 0.05), (0.0, -0.035), (-0.05, 0.05)]
        section = Contour2D.from_points([d3d.Point2D(*point) for point in points])
        beam_frame = d3d.Frame3D(d3d.Point3D(-0.25, 0.5 * self.length, 0), d3d.X3D, d3d.Z3D, -d3d.Y3D)
        return ExtrudedProfile(beam_frame, section, [], self.length, name=self.name)


class TrailingArm(Part):
    """Trailing arm from its pivot on the body to the stub axle, symmetric about its own XZ plane."""

    color = STEEL

    def __init__(self, length: float, name: str = "Trailing arm"):
        super().__init__(name)
        self.length = length

    def geometry(self):
        center = d3d.Point3D(0.05 - 0.5 * self.length, 0, 0)
        return Block(d3d.Frame3D(center, self.length * d3d.X3D, 0.06 * d3d.Y3D, 0.09 * d3d.Z3D), name=self.name)


class RearSuspension(SubAssembly):
    """Torsion beam rear axle: arms, springs and dampers are each one instance placed on both sides."""

    def __init__(self, track: float, name: str = "Rear suspension"):
        super().__init__(name)
        self.track = track
        self.beam = TorsionBeam(track - 0.36)
        self.arm = TrailingArm(0.55)
        self.spring = CoilSpring(0.11, 0.011, 0.25, turns=5, name="Rear spring")
        self.damper = Damper(0.045, 0.38, name="Rear damper")

    def children(self):
        arm_y = 0.5 * self.track - 0.17
        children = [(self.beam, d3d.OXYZ)]
        for side in (-1, 1):
            children.extend(
                [
                    (self.arm, frame(y=side * arm_y)),
                    (self.spring, frame(-0.12, side * (arm_y - 0.06), 0.0)),
                    (self.damper, frame(0.06, side * arm_y, 0.0)),
                ]
            )
        return children
