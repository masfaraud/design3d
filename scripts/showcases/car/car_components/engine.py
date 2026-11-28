"""
Inline engine: block, head, crankshaft, connecting rods and pistons placed from the crank angle.

The engine frame has its origin on the crankshaft axis, at the middle of the cylinders row: the crankshaft is along
X and the cylinders along Z.
"""

import math

import design3d as d3d
from design3d.curves import Circle2D
from design3d.primitives2d import CirclesConvexHull2D, RoundedRectangle2D
from design3d.primitives3d import Cylinder, ExtrudedProfile
from design3d.wires import Contour2D

from .base import Box, Part, SubAssembly, frame

ALUMINIUM = (0.7, 0.72, 0.75)
STEEL = (0.4, 0.4, 0.42)
# Frame whose (u, v) plane is the (Y, Z) plane and extrusion axis is X
CRANK_PLANE_FRAME = d3d.OYZX
# Draft of the forged parts, on each side of their parting plane, and of the cast parts
FORGING_DRAFT = math.radians(5)
CASTING_DRAFT = math.radians(2)


def x_rotated_frame(x: float, angle: float) -> d3d.Frame3D:
    """Frame at (x, 0, 0) rotated by angle around X: local Z goes to (0, -sin(angle), cos(angle))."""
    cos, sin = math.cos(angle), math.sin(angle)
    return d3d.Frame3D(d3d.Point3D(x, 0, 0), d3d.X3D, d3d.Vector3D(0, cos, sin), d3d.Vector3D(0, -sin, cos))


class EngineBlock(Part):
    """Cylinder block with its bores, from below the crankshaft up to the deck."""

    color = ALUMINIUM
    alpha = 0.35

    def __init__(self, cylinder_positions: list[float], bore: float, bottom: float, deck_height: float, name="Block"):
        super().__init__(name)
        self.cylinder_positions = cylinder_positions
        self.bore = bore
        self.bottom = bottom
        self.deck_height = deck_height

    @property
    def length(self):
        spacing = self.cylinder_positions[1] - self.cylinder_positions[0]
        return self.cylinder_positions[-1] - self.cylinder_positions[0] + spacing + 0.04

    @property
    def width(self):
        return self.bore + 0.07

    def geometry(self):
        outer = RoundedRectangle2D(self.length, self.width, 0.012)
        bores = [
            Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(x, 0), 0.5 * self.bore))
            for x in self.cylinder_positions
        ]
        # Cast block, demolded upwards, with machined (straight) bores
        return ExtrudedProfile(
            frame(z=self.bottom),
            outer,
            bores,
            self.deck_height - self.bottom,
            draft_angle=CASTING_DRAFT,
            inner_draft_angles=[0.0] * len(bores),
            name=self.name,
        )


class OilSump(Part):
    """Stamped oil sump below the block, its walls drafted to be drawn from a flat sheet."""

    color = (0.25, 0.25, 0.27)

    def __init__(self, length: float, width: float, top: float, depth: float, name: str = "Oil sump"):
        super().__init__(name)
        self.length = length
        self.width = width
        self.top = top
        self.depth = depth

    def geometry(self):
        # Sketch on the block mounting face, extruded downwards
        sump_frame = d3d.Frame3D(d3d.Point3D(0, 0, self.top), d3d.X3D, -d3d.Y3D, -d3d.Z3D)
        profile = RoundedRectangle2D(self.length, self.width, 0.03)
        return ExtrudedProfile(sump_frame, profile, [], self.depth, draft_angle=math.radians(8), name=self.name)


class Journal(Part):
    """Cylinder along X centered at the origin: main journals and crank pins."""

    color = STEEL

    def __init__(self, diameter: float, length: float, name: str = "Journal"):
        super().__init__(name)
        self.diameter = diameter
        self.length = length

    def geometry(self):
        return Cylinder(CRANK_PLANE_FRAME, 0.5 * self.diameter, self.length, name=self.name)


class CrankWeb(Part):
    """Crank web with its counterweight, the crank pin is along local Z at the crank radius."""

    color = STEEL

    def __init__(self, crank_radius: float, thickness: float, counterweight_radius: float, pin_boss_radius, name="Web"):
        super().__init__(name)
        self.crank_radius = crank_radius
        self.thickness = thickness
        self.counterweight_radius = counterweight_radius
        self.pin_boss_radius = pin_boss_radius

    def geometry(self):
        profile = CirclesConvexHull2D(
            [d3d.Point2D(0, -0.3 * self.counterweight_radius), d3d.Point2D(0, self.crank_radius)],
            [self.counterweight_radius, self.pin_boss_radius],
        )
        # Forged web: the parting plane is its middle plane
        return ExtrudedProfile(
            CRANK_PLANE_FRAME, profile, [], self.thickness, draft_angle=FORGING_DRAFT, symmetric=True, name=self.name
        )


class Crankshaft(SubAssembly):
    """Crankshaft: main journals between the cylinders, one throw (two webs and a pin) per cylinder."""

    def __init__(self, cylinder_positions, throw_angles, stroke: float, cylinder_spacing: float, name="Crankshaft"):
        super().__init__(name)
        self.cylinder_positions = cylinder_positions
        self.throw_angles = throw_angles
        self.cylinder_spacing = cylinder_spacing
        self.pin_length = 0.024
        self.web_thickness = 0.016
        main_length = cylinder_spacing - self.pin_length - 2 * self.web_thickness
        self.main_journal = Journal(0.045, main_length, name="Main journal")
        self.crank_pin = Journal(0.042, self.pin_length, name="Crank pin")
        self.web = CrankWeb(0.5 * stroke, self.web_thickness, 0.065, 0.028, name="Crank web")

    def children(self):
        children = []
        for x in self.cylinder_positions:
            children.append((self.main_journal, frame(x - 0.5 * self.cylinder_spacing)))
        children.append((self.main_journal, frame(self.cylinder_positions[-1] + 0.5 * self.cylinder_spacing)))
        web_offset = 0.5 * (self.pin_length + self.web_thickness)
        for x, angle in zip(self.cylinder_positions, self.throw_angles):
            pin_frame = x_rotated_frame(x, angle)
            children.append((self.crank_pin, pin_frame.translation(self.web.crank_radius * pin_frame.w)))
            children.append((self.web, x_rotated_frame(x - web_offset, angle)))
            children.append((self.web, x_rotated_frame(x + web_offset, angle)))
        return children


class ConnectingRod(Part):
    """Connecting rod in the (Y, Z) plane: big end at the origin, small end at z=length."""

    color = (0.55, 0.55, 0.58)

    def __init__(
        self,
        length: float,
        big_end_bore: float,
        small_end_bore: float,
        thickness: float = 0.02,
        wall: float = 0.009,
        name="Connecting rod",
    ):
        super().__init__(name)
        self.length = length
        self.big_end_bore = big_end_bore
        self.small_end_bore = small_end_bore
        self.thickness = thickness
        self.wall = wall

    def geometry(self):
        big_end, small_end = d3d.Point2D(0, 0), d3d.Point2D(0, self.length)
        profile = CirclesConvexHull2D(
            [big_end, small_end], [0.5 * self.big_end_bore + self.wall, 0.5 * self.small_end_bore + self.wall]
        )
        bores = [
            Contour2D.from_circle(Circle2D.from_center_and_radius(big_end, 0.5 * self.big_end_bore)),
            Contour2D.from_circle(Circle2D.from_center_and_radius(small_end, 0.5 * self.small_end_bore)),
        ]
        # Forged rod with machined (straight) bores
        return ExtrudedProfile(
            CRANK_PLANE_FRAME,
            profile,
            bores,
            self.thickness,
            draft_angle=FORGING_DRAFT,
            inner_draft_angles=[0.0, 0.0],
            symmetric=True,
            name=self.name,
        )


class Piston(Part):
    """Piston along Z, with its pin at the origin and its crown at the compression height."""

    color = (0.8, 0.8, 0.82)

    def __init__(self, diameter: float, compression_height: float, name: str = "Piston"):
        super().__init__(name)
        self.diameter = diameter
        self.compression_height = compression_height
        self.height = 1.8 * compression_height

    def geometry(self):
        center = frame(z=self.compression_height - 0.5 * self.height)
        return Cylinder(center, 0.5 * self.diameter, self.height, name=self.name)


class Engine(SubAssembly):
    """
    Inline engine built from its bore, stroke and connecting rod length.

    The pistons and connecting rods are placed from the crank angle, with evenly spaced firing intervals.
    """

    def __init__(
        self,
        number_cylinders: int,
        bore: float,
        stroke: float,
        connecting_rod_length: float,
        cylinder_spacing: float,
        crank_angle: float = 0.0,
        name: str = "Engine",
    ):
        super().__init__(name)
        self.number_cylinders = number_cylinders
        self.bore = bore
        self.stroke = stroke
        self.connecting_rod_length = connecting_rod_length
        self.crank_angle = crank_angle
        self.cylinder_positions = [
            (i - 0.5 * (number_cylinders - 1)) * cylinder_spacing for i in range(number_cylinders)
        ]
        firing_interval = 4 * math.pi / number_cylinders
        self.throw_angles = [crank_angle + i * firing_interval for i in range(number_cylinders)]

        compression_height = 0.3 * bore
        self.deck_height = 0.5 * stroke + connecting_rod_length + compression_height + 0.001
        self.block = EngineBlock(self.cylinder_positions, bore, -0.08, self.deck_height)
        half_length, half_width = 0.5 * self.block.length, 0.5 * self.block.width
        self.head = Box(
            (-half_length, -half_width - 0.02, self.deck_height),
            (half_length, half_width + 0.02, self.deck_height + 0.13),
            color=ALUMINIUM,
            name="Cylinder head",
        )
        self.cam_cover = Box(
            (-half_length + 0.01, -half_width, self.deck_height + 0.13),
            (half_length - 0.01, half_width, self.deck_height + 0.18),
            color=(0.1, 0.1, 0.1),
            name="Cam cover",
        )
        self.oil_sump = OilSump(self.block.length, self.block.width + 0.06, top=-0.08, depth=0.11)
        self.crankshaft = Crankshaft(self.cylinder_positions, self.throw_angles, stroke, cylinder_spacing)
        self.connecting_rod = ConnectingRod(connecting_rod_length, self.crankshaft.crank_pin.diameter, 0.02)
        self.piston = Piston(bore - 0.001, compression_height)

    @property
    def flange_position(self) -> float:
        """Position along the crankshaft axis of the gearbox mounting face (on the -X side)."""
        return -0.5 * self.block.length

    @property
    def top_height(self) -> float:
        return self.deck_height + 0.18

    def piston_pin_height(self, angle: float) -> float:
        crank_radius = 0.5 * self.stroke
        return crank_radius * math.cos(angle) + math.sqrt(
            self.connecting_rod_length**2 - (crank_radius * math.sin(angle)) ** 2
        )

    def children(self):
        children = [
            (self.block, d3d.OXYZ),
            (self.head, d3d.OXYZ),
            (self.cam_cover, d3d.OXYZ),
            (self.oil_sump, d3d.OXYZ),
            (self.crankshaft, d3d.OXYZ),
        ]
        crank_radius = 0.5 * self.stroke
        for x, angle in zip(self.cylinder_positions, self.throw_angles):
            pin_y, pin_z = -crank_radius * math.sin(angle), crank_radius * math.cos(angle)
            piston_z = self.piston_pin_height(angle)
            rod_angle = math.atan2(pin_y, piston_z - pin_z)
            rod_frame = x_rotated_frame(x, rod_angle).translation(d3d.Vector3D(0, pin_y, pin_z))
            children.append((self.connecting_rod, rod_frame))
            children.append((self.piston, frame(x, 0, piston_z)))
        return children
