"""
Checks of the car package: constraints on measured values, and comparisons with a reference car.
"""

import math
from dataclasses import dataclass


@dataclass
class Constraint:
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


def check_constraints(constraints: list[Constraint]):
    """Raises an error listing the violated constraints, if any."""
    violated = [constraint for constraint in constraints if not constraint.is_satisfied]
    if violated:
        raise ValueError("Constraints violated:\n" + "\n".join(f"  {c}" for c in violated))


@dataclass
class ReferenceCheck:
    """Value measured on the model compared with the value of the reference car, within a relative tolerance."""

    name: str
    value: float
    reference: float
    tolerance: float = 0.01
    unit: str = "mm"
    scale: float = 1000.0

    @property
    def deviation(self) -> float:
        return (self.value - self.reference) / self.reference

    @property
    def is_satisfied(self) -> bool:
        return abs(self.deviation) <= self.tolerance

    def __str__(self):
        status = "OK" if self.is_satisfied else "DEVIATION"
        return (
            f"{self.name}: {self.value * self.scale:.0f} {self.unit}, reference {self.reference * self.scale:.0f}"
            f" {self.unit} ({self.deviation:+.1%}, tolerance {self.tolerance:.0%}) {status}"
        )
