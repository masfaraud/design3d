"""
Occupant model for the ergonomic constraints of the car package.

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
