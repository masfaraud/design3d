"""
Recursive data model of the car showcase.

A product is a tree of components: a SubAssembly places child components in its own frame, a Part is a leaf that
builds its geometry. The same component instance can be placed several times (four identical wheels, three pistons),
its geometry is then built only once.

Coordinates follow the usual automotive convention: X rearwards, Y to the right, Z upwards, in meters.
"""

import math
from functools import cached_property

import design3d as d3d
from design3d.core import Assembly
from design3d.primitives3d import Block, Cylinder
from design3d.wires import ClosedPolygon2D


class Component:
    """Node of the product tree."""

    def __init__(self, name: str):
        self.name = name

    def to_design3d(self):
        """Design3d object of this component, expressed in its own frame (built once and cached)."""
        return self.design3d_object

    @cached_property
    def design3d_object(self):
        raise NotImplementedError

    def tree(self, indent: int = 0) -> str:
        """Text view of the product tree."""
        return "  " * indent + f"{self.name} ({self.__class__.__name__})"


class Part(Component):
    """Leaf of the product tree: a single solid."""

    color = None
    alpha = 1.0

    def geometry(self):
        """Builds the solid of the part in its own frame."""
        raise NotImplementedError

    @cached_property
    def design3d_object(self):
        primitive = self.geometry()
        primitive.name = self.name
        if self.color is not None:
            primitive.color = self.color
        primitive.alpha = self.alpha
        return primitive


class SubAssembly(Component):
    """Node of the product tree: components placed in the frame of the subassembly."""

    def children(self) -> list[tuple[Component, d3d.Frame3D]]:
        """Child components with the frames positioning them in the subassembly frame."""
        raise NotImplementedError

    @cached_property
    def placed_children(self):
        return self.children()

    @cached_property
    def design3d_object(self):
        components = [child.to_design3d() for child, _ in self.placed_children]
        positions = [frame for _, frame in self.placed_children]
        return Assembly(components, positions, name=self.name)

    def tree(self, indent: int = 0) -> str:
        lines = [super().tree(indent)]
        counts = {}
        for child, _ in self.placed_children:
            counts[id(child)] = counts.get(id(child), 0) + 1
        seen = set()
        for child, _ in self.placed_children:
            if id(child) in seen:
                continue
            seen.add(id(child))
            child_lines = child.tree(indent + 1).split("\n")
            if counts[id(child)] > 1:
                child_lines[0] += f" x{counts[id(child)]}"
            lines.extend(child_lines)
        return "\n".join(lines)


# Placement helpers


def frame(x: float = 0.0, y: float = 0.0, z: float = 0.0, u=d3d.X3D, v=d3d.Y3D, w=d3d.Z3D) -> d3d.Frame3D:
    """Frame at (x, y, z), axes default to the parent ones."""
    return d3d.Frame3D(d3d.Point3D(x, y, z), u, v, w)


def z_rotated_frame(x: float, y: float, z: float, angle: float) -> d3d.Frame3D:
    """Frame at (x, y, z) rotated around the vertical axis."""
    cos, sin = math.cos(angle), math.sin(angle)
    return d3d.Frame3D(d3d.Point3D(x, y, z), d3d.Vector3D(cos, sin, 0), d3d.Vector3D(-sin, cos, 0), d3d.Z3D)


def mirrored_frame(x: float, y: float, z: float) -> d3d.Frame3D:
    """
    Frame placing on the right-hand side a component defined for the left-hand side, such as a wheel.

    A true mirror would give an indirect frame, the component is rotated by a half turn around X instead: its outer
    side goes from local -Y to +Y, and it must be symmetric with respect to its own XY plane.
    """
    return d3d.Frame3D(d3d.Point3D(x, y, z), d3d.X3D, -d3d.Y3D, -d3d.Z3D)


def frame_along(point1: d3d.Point3D, point2: d3d.Point3D) -> d3d.Frame3D:
    """Frame at point1 whose w axis points towards point2."""
    w = d3d.Vector3D(point2.x - point1.x, point2.y - point1.y, point2.z - point1.z).unit_vector()
    u = w.deterministic_unit_normal_vector()
    return d3d.Frame3D(point1, u, w.cross(u), w)


# Generic parts


class Box(Part):
    """Axis-aligned box between two opposite corners."""

    def __init__(self, corner1: tuple, corner2: tuple, color=None, alpha: float = 1.0, name: str = "Box"):
        super().__init__(name)
        self.corner1 = corner1
        self.corner2 = corner2
        self.color = color
        self.alpha = alpha

    @classmethod
    def centered(cls, size_x: float, size_y: float, size_z: float, color=None, alpha: float = 1.0, name: str = "Box"):
        """Box centered at the origin."""
        half_sizes = (0.5 * size_x, 0.5 * size_y, 0.5 * size_z)
        return cls(tuple(-size for size in half_sizes), half_sizes, color=color, alpha=alpha, name=name)

    def geometry(self):
        center = d3d.Point3D(*(0.5 * (a + b) for a, b in zip(self.corner1, self.corner2)))
        sizes = [abs(b - a) for a, b in zip(self.corner1, self.corner2)]
        return Block(d3d.Frame3D(center, sizes[0] * d3d.X3D, sizes[1] * d3d.Y3D, sizes[2] * d3d.Z3D), name=self.name)


class Tube(Part):
    """Cylinder whose axis goes from point1 to point2."""

    def __init__(self, point1: tuple, point2: tuple, diameter: float, color=None, name: str = "Tube"):
        super().__init__(name)
        self.point1 = d3d.Point3D(*point1)
        self.point2 = d3d.Point3D(*point2)
        self.diameter = diameter
        self.color = color

    @property
    def length(self):
        return self.point1.point_distance(self.point2)

    def geometry(self):
        axis_frame = frame_along(self.point1, self.point2)
        center_frame = axis_frame.translation(0.5 * self.length * axis_frame.w)
        return Cylinder(center_frame, 0.5 * self.diameter, self.length, name=self.name)


def circles_hull(circles: list[tuple[float, float, float]], number_points: int = 24) -> ClosedPolygon2D:
    """
    2D profile enveloping circles, such as a crank web or a connecting rod.

    :param circles: (x, y, radius) of each circle
    """
    points = []
    for x, y, radius in circles:
        for i in range(number_points):
            angle = 2 * math.pi * i / number_points
            points.append(d3d.Point2D(x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return ClosedPolygon2D.points_convex_hull(points)
