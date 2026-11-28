"""
Parametric car showcase: a recursive product tree built from architecture parameters.

Each subassembly (body, engine, drivetrain, suspensions...) is a class instantiated from the parameters below,
which can in turn instantiate other subassemblies and parts. The dimensions are inspired by a compact hatchback
with a transverse 1.2 L three-cylinder petrol engine (orders of magnitude, not a reference model).

Coordinates follow the usual automotive convention: X rearwards, Y to the right, Z upwards, in meters, with the
origin on the ground below the front axle.
"""

import math
from dataclasses import dataclass, field

from car_components.base import Box, SubAssembly, frame, mirrored_frame
from car_components.biw import BodyInWhite
from car_components.checks import Constraint, ReferenceCheck, check_constraints
from car_components.drivetrain import Drivetrain
from car_components.engine import Engine
from car_components.ergonomics import Occupant
from car_components.interior import Exhaust, Seat
from car_components.steering import Steering
from car_components.suspension import FrontSuspension, RearSuspension
from car_components.wheel import Wheel

import design3d as d3d
from design3d.core import VolumeModel
from design3d.faces import PlaneFace3D
from design3d.surfaces import Plane3D

# Architecture parameters


@dataclass
class BodyParameters:
    length: float = 4.367
    width: float = 1.852
    height: float = 1.441
    wheelbase: float = 2.675
    front_overhang: float = 0.895
    front_track: float = 1.56
    rear_track: float = 1.55
    ground_clearance: float = 0.14


@dataclass
class WheelParameters:
    tyre_width: float = 0.225
    tyre_aspect_ratio: float = 0.45
    rim_diameter_inch: float = 17
    rim_width_inch: float = 7.5
    brake_disc_diameter: float = 0.304
    brake_disc_thickness: float = 0.026


@dataclass
class EngineParameters:
    number_cylinders: int = 3
    bore: float = 0.075
    stroke: float = 0.0905
    connecting_rod_length: float = 0.13
    cylinder_spacing: float = 0.084
    crank_angle: float = math.radians(30)
    # Crankshaft axis position, relative to the front wheels center
    crank_x: float = -0.21
    crank_y: float = 0.12
    crank_z: float = 0.09


@dataclass
class ErgonomicsParameters:
    # Driver H-point (hip joint), the driver sits on the left-hand side
    driver_h_point: tuple[float, float, float] = (1.5, -0.37, 0.44)
    # Steering wheel center relative to the driver H-point: forward and upward
    steering_wheel_offset: tuple[float, float] = (0.47, 0.5)
    # Horizontal distance between the front and rear H-points, and height difference (rear passengers sit higher)
    couple_distance: float = 0.8
    rear_h_point_rise: float = 0.04
    # Constraints
    steering_wheel_reach: tuple[float, float] = (0.4, 0.55)
    min_driver_knee_clearance: float = 0.08
    min_rear_knee_clearance: float = 0.05
    occupant: Occupant = field(default_factory=Occupant)


@dataclass
class ReferenceCar:
    """Published figures of the reference car (third generation Peugeot 308, 1.2 PureTech 130), to check the model."""

    length: float = 4.367
    # Without the mirrors
    width: float = 1.852
    height: float = 1.441
    ground_clearance: float = 0.14
    displacement: float = 1.199e-3


@dataclass
class CarParameters:
    body: BodyParameters = field(default_factory=BodyParameters)
    front_wheels: WheelParameters = field(default_factory=WheelParameters)
    rear_wheels: WheelParameters = field(
        default_factory=lambda: WheelParameters(brake_disc_diameter=0.268, brake_disc_thickness=0.012)
    )
    engine: EngineParameters = field(default_factory=EngineParameters)
    ergonomics: ErgonomicsParameters = field(default_factory=ErgonomicsParameters)


class Car(SubAssembly):
    """Whole car: the subassemblies are placed from the architecture parameters."""

    def __init__(self, parameters: CarParameters, name: str = "Car"):
        super().__init__(name)
        self.parameters = parameters
        body = parameters.body
        engine = parameters.engine

        self.front_wheel = Wheel(**vars(parameters.front_wheels), name="Front wheel")
        self.rear_wheel = Wheel(**vars(parameters.rear_wheels), name="Rear wheel")
        self.wheel_center_height = self.front_wheel.radius

        self.body_in_white = BodyInWhite(
            body.length,
            body.width,
            body.height,
            body.wheelbase,
            body.front_overhang,
            body.ground_clearance,
            self.wheel_center_height,
        )
        self.front_suspension = FrontSuspension(body.front_track)
        self.rear_suspension = RearSuspension(body.rear_track)

        self.engine = Engine(
            engine.number_cylinders,
            engine.bore,
            engine.stroke,
            engine.connecting_rod_length,
            engine.cylinder_spacing,
            engine.crank_angle,
        )
        # Transverse engine: its crankshaft (local X) is along the car Y axis, and the gearbox on the left-hand side
        self.engine_frame = d3d.Frame3D(
            d3d.Point3D(engine.crank_x, engine.crank_y, self.wheel_center_height + engine.crank_z),
            d3d.Y3D,
            -d3d.X3D,
            d3d.Z3D,
        )
        self.drivetrain = Drivetrain(
            (engine.crank_x, engine.crank_z),
            flange_y=engine.crank_y + self.engine.flange_position,
            hub_y=0.5 * body.front_track - 0.16,
        )

        # Occupants: the steering wheel and the rear bench are placed from the driver H-point
        ergonomics = parameters.ergonomics
        h_x, h_y, h_z = ergonomics.driver_h_point
        forward, upward = ergonomics.steering_wheel_offset
        steering_wheel_center = (h_x - forward, h_y, h_z + upward - self.wheel_center_height)
        self.steering = Steering(body.front_track, steering_wheel_center)
        self.rear_h_point = (h_x + ergonomics.couple_distance, 0.0, h_z + ergonomics.rear_h_point_rise)

        self.front_seat = Seat(0.52, name="Front seat")
        self.rear_bench = Seat(1.25, name="Rear bench")
        # Under the rear bench, ahead of the torsion beam
        self.fuel_tank = Box(
            (body.wheelbase - 0.875, -0.55, body.ground_clearance + 0.01),
            (body.wheelbase - 0.375, 0.55, body.ground_clearance + 0.18),
            color=(0.15, 0.15, 0.15),
            name="Fuel tank",
        )
        engine_front = engine.crank_x - 0.5 * self.engine.block.width
        self.exhaust = Exhaust(
            (engine_front, engine.crank_y, self.wheel_center_height + engine.crank_z + 0.1),
            muffler_x=body.wheelbase + 0.45,
            floor_height=self.body_in_white.floor_height,
            ground_clearance=body.ground_clearance,
        )
        self.ergonomic_constraints = self.compute_ergonomic_constraints()
        check_constraints(self.ergonomic_constraints)

    def compute_ergonomic_constraints(self) -> list[Constraint]:
        """Measures the package on the placed seats and steering wheel."""
        ergonomics = self.parameters.ergonomics
        occupant = ergonomics.occupant
        h_x, _, h_z = ergonomics.driver_h_point

        # Steering wheel: center in the car frame, and lowest point of its rim
        column = self.steering.column
        wheel_x, wheel_z = column.point2.x, column.point2.z + self.wheel_center_height
        axis = (column.point2 - column.point1).unit_vector()
        rim_radius = 0.5 * self.steering.steering_wheel.rim.diameter
        rim_bottom_z = wheel_z - rim_radius * math.sqrt(1 - axis.z**2)
        _, driver_knee_z = occupant.knee_position(h_x, h_z)

        # Rear passenger knee, facing the rear face of the front seat backrest
        rear_x, _, rear_z = self.rear_h_point
        rear_knee_x, rear_knee_z = occupant.knee_position(rear_x, rear_z)
        backrest_rear_x = h_x + self.front_seat.backrest_rear_x(rear_knee_z - h_z)

        reach_min, reach_max = ergonomics.steering_wheel_reach
        return [
            Constraint("Steering wheel reach", h_x - wheel_x, reach_min, reach_max),
            Constraint(
                "Driver knee to steering wheel", rim_bottom_z - driver_knee_z, ergonomics.min_driver_knee_clearance
            ),
            Constraint(
                "Rear knee to front backrest", rear_knee_x - backrest_rear_x, ergonomics.min_rear_knee_clearance
            ),
        ]

    def reference_checks(self, reference: ReferenceCar) -> list:
        """Measures the geometry of the model and compares it with the reference car."""
        body = self.parameters.body
        engine = self.engine
        bounding_box = self.to_design3d().bounding_box
        # Bounding boxes of the placed subassemblies, in the car frame
        placed = list(zip([child for child, _ in self.placed_children], self.to_design3d().primitives))
        wheels = (self.front_wheel, self.rear_wheel)
        wheel_boxes = [primitive.bounding_box for child, primitive in placed if child in wheels]
        lowest_body_point = min(primitive.bounding_box.zmin for child, primitive in placed if child not in wheels)
        tyres_half_width = max(max(-box.ymin, box.ymax) for box in wheel_boxes)
        displacement = engine.number_cylinders * 0.25 * math.pi * engine.bore**2 * engine.stroke
        return [
            ReferenceCheck("Overall length", bounding_box.xmax - bounding_box.xmin, reference.length),
            ReferenceCheck("Overall width", bounding_box.ymax - bounding_box.ymin, reference.width),
            ReferenceCheck("Overall height", bounding_box.zmax - bounding_box.zmin, reference.height),
            ReferenceCheck("Displacement", displacement, reference.displacement, unit="cm³", scale=1e6),
            Constraint(
                "Ground clearance (lowest point out of the wheels)", lowest_body_point, reference.ground_clearance
            ),
            Constraint("Tyres inside the body width", 0.5 * body.width - tyres_half_width, 0.0),
        ]

    def children(self):
        body = self.parameters.body
        z_wheels = self.wheel_center_height
        h_x, h_y, h_z = self.parameters.ergonomics.driver_h_point
        front_axle = frame(0, 0, z_wheels)
        rear_axle = frame(body.wheelbase, 0, z_wheels)
        return [
            (self.body_in_white, d3d.OXYZ),
            # The same wheel instances are placed on both sides
            (self.front_wheel, frame(0, -0.5 * body.front_track, z_wheels)),
            (self.front_wheel, mirrored_frame(0, 0.5 * body.front_track, z_wheels)),
            (self.rear_wheel, frame(body.wheelbase, -0.5 * body.rear_track, z_wheels)),
            (self.rear_wheel, mirrored_frame(body.wheelbase, 0.5 * body.rear_track, z_wheels)),
            (self.front_suspension, front_axle),
            (self.rear_suspension, rear_axle),
            (self.engine, self.engine_frame),
            (self.drivetrain, front_axle),
            (self.steering, front_axle),
            # The same front seat instance is placed on both sides
            (self.front_seat, frame(h_x, h_y, h_z)),
            (self.front_seat, frame(h_x, -h_y, h_z)),
            (self.rear_bench, frame(*self.rear_h_point)),
            (self.fuel_tank, d3d.OXYZ),
            (self.exhaust, d3d.OXYZ),
        ]


car = Car(CarParameters())
print(car.tree())
print("Ergonomics:")
for constraint in car.ergonomic_constraints:
    print(f"  {constraint}")
print("Checks against the reference car:")
for check in car.reference_checks(ReferenceCar()):
    print(f"  {check}")

ground = PlaneFace3D.from_surface_rectangular_cut(Plane3D(d3d.OXYZ), -1.5, 4.5, -1.5, 1.5)
ground.name = "Ground"
ground.color = (0.44, 0.43, 0.41)

scene = VolumeModel([ground, car.to_design3d()], name="Car")
scene.babylonjs()
scene.to_step("car")
