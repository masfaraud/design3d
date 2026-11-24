"""
Ergonomic constraints of the car package, checked on the placed seats and steering wheel.

The occupant is reduced to a side-view manikin: the H-point (hip joint) and the knee, at the end of the thigh.
"""

import math
from dataclasses import dataclass


@dataclass
class Occupant:
    """Side-view manikin, the default values are those of a tall (95th percentile) adult."""

    thigh_length: float = 0.46
    thigh_angle: float = math.radians(12)

    def knee_position(self, h_point_x: float, h_point_z: float) -> tuple[float, float]:
        """(x, z) of the knee, forward of the H-point (towards -X) and slightly above it."""
        return (
            h_point_x - self.thigh_length * math.cos(self.thigh_angle),
            h_point_z + self.thigh_length * math.sin(self.thigh_angle),
        )


@dataclass
class ErgonomicConstraint:
    """Value measured on the package, which must lie between its bounds."""

    name: str
    value: float
    minimum: float = -math.inf
    maximum: float = math.inf

    @property
    def is_satisfied(self) -> bool:
        return self.minimum <= self.value <= self.maximum

    def __str__(self):
        bounds = []
        if self.minimum > -math.inf:
            bounds.append(f">= {self.minimum * 1000:.0f}")
        if self.maximum < math.inf:
            bounds.append(f"<= {self.maximum * 1000:.0f}")
        status = "OK" if self.is_satisfied else "VIOLATED"
        return f"{self.name}: {self.value * 1000:.0f} mm ({' and '.join(bounds)} mm) {status}"


def check_constraints(constraints: list[ErgonomicConstraint]):
    """Raises an error listing the violated constraints, if any."""
    violated = [constraint for constraint in constraints if not constraint.is_satisfied]
    if violated:
        raise ValueError("Ergonomic constraints violated:\n" + "\n".join(f"  {c}" for c in violated))
