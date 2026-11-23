"""
Motorcycle design showcase.

The goal of this script is to model a motorcycle whose dimensions are close to the ones of a 2015 Yamaha MT-125.
The model stays high level: it is driven by a few architecture parameters (tyre sizes, wheelbase, steering geometry,
swingarm...), from which the hardpoints of the motorcycle are computed. The parts are then built and placed from
these hardpoints, with detail parameters that do not change the architecture.

Reference data of the MT-125 (2014-2015): wheelbase 1355 mm, caster 25°, trail 89 mm, tyres 100/80-17 and
130/70-17, brake disks 292 mm (front) and 230 mm (rear), seat height 810 mm, overall length x width x height
1955 x 740 x 1040 mm, ground clearance 140 mm, fuel tank 11.5 L. Sources: Yamaha MT125 factsheets,
moto-data.net, bikez.net.

Frame of reference: the origin is the contact point of the front tyre on the ground, X points backward (from the
front wheel to the rear wheel), Y points to the right of the rider (who faces -X) and Z points up.
"""

import math

import numpy as np

import design3d as d3d
from design3d.core import Assembly
from design3d.curves import Circle2D
from design3d.edges import Arc2D, LineSegment2D
from design3d.faces import PlaneFace3D
from design3d.primitives2d import ClosedRoundedLineSegments2D
from design3d.primitives3d import (
    Cylinder,
    ExtrudedProfile,
    HollowCylinder,
    Loft,
    OpenRoundedLineSegments3D,
    RevolvedProfile,
    Sweep,
)
from design3d.surfaces import Plane3D
from design3d.wires import ClosedPolygon2D, Contour2D


def tyre_dimensions(tyre_size: str) -> tuple[float, float, float]:
    """
    Dimensions of a tyre from its size marking, for instance "100/80-17".

    :param tyre_size: width in mm, sidewall height as a percentage of the width, and rim diameter in inches.
    :return: the width, outer diameter and rim diameter of the tyre, in meters.
    """
    width_and_ratio, rim_inches = tyre_size.split("-")
    width_mm, aspect_ratio = width_and_ratio.split("/")
    width = float(width_mm) / 1000
    rim_diameter = float(rim_inches) * 0.0254
    return width, rim_diameter + 2 * width * float(aspect_ratio) / 100, rim_diameter


# ======================================================================================================================
# Architecture parameters: they drive the overall geometry of the motorcycle
# ======================================================================================================================

# Tyres, as marked on their sidewall
front_tyre_size = "100/80-17"
rear_tyre_size = "130/70-17"

# Steering geometry
wheelbase = 1.355  # horizontal distance between the wheel axles
caster_angle = math.radians(25)  # angle between the steering axis and the vertical
trail = 0.089  # ground distance between the front tyre contact point and the steering axis

# Fork length, from the front axle to the top of the upper crown, along the fork tubes (estimated value)
fork_length = 0.700

# Swingarm, from the rear axle to its pivot on the frame (these values are estimated)
swingarm_length = 0.560
swingarm_angle = math.radians(10)  # positive when the pivot is higher than the rear axle

# Rear shock (estimated values): its lower mount is on the swingarm, at a distance from the pivot along the arm and
# above its axis; its upper mount is on the frame, given relatively to the swingarm pivot
shock_lower_mount_distance = 0.150
shock_lower_mount_height = 0.050
shock_upper_mount_offset = d3d.Vector3D(0.0, 0, 0.300)

# Engine (estimated position): single cylinder, inclined forward, the front sprocket being on the gearbox output shaft,
# close to the swingarm pivot
crankshaft_center = d3d.Point3D(0.560, 0, 0.330)
cylinder_inclination = math.radians(15)  # forward, from the vertical
engine_bore = 0.052
engine_stroke = 0.0586
front_sprocket_offset = d3d.Vector3D(-0.070, 0, -0.025)  # from the swingarm pivot

# Chain drive: 428 chain (pitch 1/2 inch)
chain_pitch = 0.0127
front_sprocket_teeth = 14
rear_sprocket_teeth = 48

# Ground clearance of the MT-125, used to check the model
target_ground_clearance = 0.140

# Overall dimensions of the MT-125, used to check the model (they do not drive it)
target_length = 1.955
target_width = 0.740
target_height = 1.040

# ======================================================================================================================
# Derived architecture values and hardpoints, in the motorcycle frame of reference
# ======================================================================================================================

front_tyre_width, front_tyre_diameter, front_rim_diameter = tyre_dimensions(front_tyre_size)
rear_tyre_width, rear_tyre_diameter, rear_rim_diameter = tyre_dimensions(rear_tyre_size)
front_wheel_radius = 0.5 * front_tyre_diameter
rear_wheel_radius = 0.5 * rear_tyre_diameter

# The fork offset is the distance between the front axle and the steering axis, that gives the trail
fork_offset = front_wheel_radius * math.sin(caster_angle) - trail * math.cos(caster_angle)
if fork_offset <= 0:
    raise ValueError("The trail is too long for this caster angle and front wheel: the fork offset is negative.")

# Unit vector of the steering axis, pointing up and backward
steering_axis = d3d.Vector3D(math.sin(caster_angle), 0, math.cos(caster_angle))

front_contact_point = d3d.Point3D(0, 0, 0)
front_axle_center = d3d.Point3D(0, 0, front_wheel_radius)
steering_axis_ground_point = d3d.Point3D(-trail, 0, 0)
rear_axle_center = d3d.Point3D(wheelbase, 0, rear_wheel_radius)
rear_contact_point = d3d.Point3D(wheelbase, 0, 0)
swingarm_pivot = rear_axle_center + swingarm_length * d3d.Vector3D(
    -math.cos(swingarm_angle), 0, math.sin(swingarm_angle)
)
# Swingarm frame: origin at the pivot, u along the arm toward the rear axle, v to the right, w up
swingarm_frame = d3d.Frame3D(
    swingarm_pivot,
    d3d.Vector3D(math.cos(swingarm_angle), 0, -math.sin(swingarm_angle)),
    d3d.Y3D,
    d3d.Vector3D(math.sin(swingarm_angle), 0, math.cos(swingarm_angle)),
)
shock_lower_mount = swingarm_frame.local_to_global_coordinates(
    d3d.Point3D(shock_lower_mount_distance, 0, shock_lower_mount_height)
)
shock_upper_mount = swingarm_pivot + shock_upper_mount_offset
front_sprocket_center = swingarm_pivot + front_sprocket_offset
cylinder_axis = d3d.Vector3D(-math.sin(cylinder_inclination), 0, math.cos(cylinder_inclination))


def sprocket_pitch_radius(number_teeth: int) -> float:
    return 0.5 * chain_pitch / math.sin(math.pi / number_teeth)


front_sprocket_radius = sprocket_pitch_radius(front_sprocket_teeth)
rear_sprocket_radius = sprocket_pitch_radius(rear_sprocket_teeth)
sprockets_distance = front_sprocket_center.point_distance(rear_axle_center)
# Number of chain links (standard formula for two sprockets)
chain_links = (
    2 * sprockets_distance / chain_pitch
    + 0.5 * (front_sprocket_teeth + rear_sprocket_teeth)
    + chain_pitch * ((rear_sprocket_teeth - front_sprocket_teeth) / (2 * math.pi)) ** 2 / sprockets_distance
)

# ======================================================================================================================
# Detail parameters: they shape the parts without changing the architecture
# ======================================================================================================================

# Tyres and rims
tyre_thickness = 0.008
front_rim_width = 2.70 * 0.0254
rear_rim_width = 3.50 * 0.0254

# Brake disks
front_brake_disk_outer_diameter = 0.292
front_brake_disk_inner_diameter = 0.250
front_brake_screw_diameter = 0.220
front_disk_number_screws = 6
front_disk_screwholes_diameter = 0.012
front_brake_disk_offset = -0.050  # on the left side
front_brake_width = 0.0045
rear_brake_disk_outer_diameter = 0.230
rear_brake_disk_inner_diameter = 0.185
rear_brake_screw_diameter = 0.150
rear_disk_number_screws = 5
rear_disk_screwholes_diameter = 0.010
rear_brake_disk_offset = 0.055  # on the right side, the chain being on the left side
rear_brake_width = 0.005

# Fork
tube_diameter = 0.041
front_axle_diameter = 0.015
crown_width = 0.020
crown_tube_outer_diameter = tube_diameter + 0.012
crowns_distance = 0.170
tyre_width_margin = 0.015
tubes_spacing = tube_diameter + front_tyre_width + 2 * tyre_width_margin
fork_pivot_diameter = 0.030
fork_pivot_inner_diameter = 0.026
crown_pivot_outer_diameter = fork_pivot_diameter + 0.012
tube_height = fork_length
tyre_crown_clearance = fork_length - front_wheel_radius - crowns_distance - 2 * crown_width
if tyre_crown_clearance < 0.035:
    raise ValueError(f"The fork is too short: {1000 * tyre_crown_clearance:.0f} mm between the tyre and the crown.")

# Front wheel bearings
front_bearing_d = front_axle_diameter
front_bearing_D = 0.042
front_bearing_B = 0.013
front_bearing_spacing = 0.090

# Rear wheel bearings and axle
rear_axle_diameter = 0.015
rear_bearing_D = 0.042
rear_bearing_B = 0.013
rear_bearing_spacing = 0.110

# Chain line: the chain is on the left side (Y < 0), between the rear tyre and the swingarm arm
chain_side = -1
chain_width = 0.012
chain_tyre_clearance = 0.020
chain_arm_clearance = 0.012
chain_line = chain_side * (0.5 * rear_tyre_width + chain_tyre_clearance + 0.5 * chain_width)

# Swingarm
swingarm_arm_width = 0.028
swingarm_arm_heights = (0.075, 0.060, 0.045)  # at the pivot, in the middle and at the rear axle
swingarm_arm_spacing = 2 * (abs(chain_line) + 0.5 * chain_width + chain_arm_clearance) + swingarm_arm_width
swingarm_pivot_tube_diameter = 0.045
swingarm_cross_member_distance = 0.120  # from the pivot, along the arm
swingarm_cross_member_size = 0.050

# Frame: steel twin-spar frame, from the steering head to the swingarm pivot plates, and rear subframe. Points are
# given as (x, z) in the motorcycle frame of reference, the spars and rails being symmetric with respect to the XZ plane
frame_head_tube_outer_diameter = fork_pivot_diameter + 0.016
spar_points = [(0.325, 0.800), (0.560, 0.715), (0.720, 0.620), (0.785, 0.500), (0.800, 0.340)]
spar_half_spacings = [0.040, 0.110, 0.150, 0.155, 0.155]  # distance from the XZ plane to the spar section centers
spar_sections = [(0.035, 0.100), (0.030, 0.065), (0.030, 0.070), (0.030, 0.110), (0.030, 0.110)]  # width, height
subframe_rail_points = [(0.600, 0.700), (1.000, 0.735), (1.480, 0.815)]
subframe_rail_half_spacing = 0.095
subframe_stay_points = [(0.790, 0.470), (1.150, 0.745)]
subframe_tube_diameter = 0.025

# Engine
crankcase_profile = [(0.460, 0.215), (0.760, 0.230), (0.770, 0.350), (0.700, 0.440), (0.520, 0.430), (0.450, 0.320)]
crankcase_right_side = 0.120  # the left side is set by the chain line, the front sprocket being outside the crankcase
cylinder_block_size = 0.100
cylinder_block_distance = (0.070, 0.200)  # from the crankshaft along the cylinder axis
cylinder_head_size = 0.115
cylinder_head_height = 0.080

# Sprockets
sprocket_width = 0.006
sprocket_tooth_height = 0.008
chain_height = 0.012

# Rear shock
shock_eye_diameter = 0.030
shock_eye_width = 0.025
shock_rod_diameter = 0.014
shock_body_diameter = 0.046
shock_spring_outer_diameter = 0.066
shock_spring_inner_diameter = 0.052

# Handlebar
crown_handlebar_offset = 0.050
handlebar_diameter = 0.028
handlebar_span = 0.650
handlebar_angle = math.radians(15)
handlebar_offset = 0.045
handlebar_base_width = 0.150

# Colors
tyre_black = (0.15, 0.15, 0.15)
asphalt = (112 / 256, 110 / 256, 106 / 256)
frame_grey = (0.27, 0.28, 0.29)  # dark painted steel
engine_grey = (0.33, 0.33, 0.34)  # cast aluminium, painted dark grey
chain_dark = (0.19, 0.19, 0.2)
steel = (0.55, 0.55, 0.56)
spring_red = (0.55, 0.16, 0.13)

# Steering head: middle of the frame pivot, between the fork crowns, on the steering axis
steering_head_center = (
    front_axle_center
    + fork_offset * d3d.Vector3D(math.cos(caster_angle), 0, -math.sin(caster_angle))
    + (tube_height - 0.5 * crowns_distance - crown_width) * steering_axis
)

# ======================================================================================================================
# Parts
# ======================================================================================================================

# Ground
ground_plane = Plane3D(d3d.OXYZ)
ground = PlaneFace3D.from_surface_rectangular_cut(ground_plane, -0.5, wheelbase + 0.5, -0.5, 0.5)
ground.name = "Ground"
ground.color = asphalt


def isohex(diameter: float):
    ISO_HEX_WIDTH_ACROSS_FLATS = {
        1.6: 3.2,
        2: 4,
        2.5: 5,
        3: 5.5,
        4: 7,
        5: 8,
        6: 10,
        7: 11,
        8: 13,
        10: 17,
        12: 19,
        14: 22,
        16: 24,
        18: 27,
        20: 30,
        22: 32,
        24: 36,
        27: 41,
        30: 46,
        33: 50,
        36: 55,
        39: 60,
        42: 65,
        45: 70,
        48: 75,
        52: 80,
        56: 85,
        60: 90,
        64: 95,
    }
    if diameter / 1000 in ISO_HEX_WIDTH_ACROSS_FLATS:
        s = ISO_HEX_WIDTH_ACROSS_FLATS[diameter / 1000] / 1000
    else:
        s = 1.47 * diameter + 0.0018
    e = s / math.cos(math.pi / 6)

    return ClosedPolygon2D([d3d.Point2D(0, e / 2).rotation(d3d.O2D, i * math.pi / 3) for i in range(6)])


def hexnut(diameter: float, height: float, name="Hex nut"):
    contour = isohex(diameter=diameter)
    return ExtrudedProfile(
        d3d.OXYZ,
        outer_contour2d=contour,
        inner_contours2d=[Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.O2D, 0.5 * diameter))],
        extrusion_length=height,
        name=name,
    )


def radial_bearing(d, D, B, name="Bearing"):
    return HollowCylinder(d3d.OXYZ, inner_radius=0.5 * d, outer_radius=0.5 * D, length=B, name=name)


def tyre(rim_diameter: float, rim_width: float, diameter: float, width: float, tyre_thickness: float, name="Tyre"):
    p1 = d3d.Point2D(-0.5 * rim_width, 0.5 * rim_diameter)
    p2 = d3d.Point2D(-0.5 * rim_width, 0.5 * rim_diameter + 0.25 * (diameter - rim_diameter - width))
    p3 = d3d.Point2D(-0.5 * width, 0.5 * (diameter - width))
    p4 = d3d.Point2D(0.5 * width, 0.5 * (diameter - width))
    p5 = d3d.Point2D(0.5 * rim_width, 0.5 * rim_diameter + 0.25 * (diameter - rim_diameter - width))
    p6 = d3d.Point2D(0.5 * rim_width, 0.5 * rim_diameter)
    p7 = p6 - tyre_thickness * d3d.X3D
    p8 = p5 - tyre_thickness * d3d.X3D
    p9 = p4 - tyre_thickness * d3d.X3D
    p10 = p3 + tyre_thickness * d3d.X3D
    p11 = p2 + tyre_thickness * d3d.X3D
    p12 = p1 + tyre_thickness * d3d.X3D

    front_tyre_contour = Contour2D(
        [
            LineSegment2D(p1, p2),
            LineSegment2D(p2, p3),
            Arc2D(
                Circle2D.from_center_and_radius(d3d.Point2D(0, 0.5 * (diameter - width)), 0.5 * width, is_trigo=False),
                p3,
                p4,
            ),
            LineSegment2D(p4, p5),
            LineSegment2D(p5, p6),
            LineSegment2D(p6, p7),
            LineSegment2D(p7, p8),
            LineSegment2D(p8, p9),
            Arc2D(
                Circle2D.from_center_and_radius(
                    d3d.Point2D(0, 0.5 * (diameter - width)), 0.5 * width - tyre_thickness, is_trigo=True
                ),
                p9,
                p10,
            ),
            LineSegment2D(p10, p11),
            LineSegment2D(p11, p12),
            LineSegment2D(p12, p1),
        ]
    )
    return RevolvedProfile(d3d.OYZX, front_tyre_contour, axis_point=d3d.O3D, axis=d3d.Y3D, color=tyre_black, name=name)


def rim(rim_diameter: float, rim_width: float, hook_height=0.007, thickness=0.008, name="Rim"):
    p1 = d3d.Point2D(-0.5 * rim_width, 0.5 * rim_diameter)
    p2 = d3d.Point2D(-0.5 * rim_width, 0.5 * rim_diameter + hook_height)
    p3 = d3d.Point2D(-0.5 * rim_width - hook_height, 0.5 * rim_diameter + hook_height)
    p4 = d3d.Point2D(-0.5 * rim_width - hook_height, 0.5 * rim_diameter - thickness)
    p5 = d3d.Point2D(0.5 * rim_width + hook_height, 0.5 * rim_diameter - thickness)
    p6 = d3d.Point2D(0.5 * rim_width + hook_height, 0.5 * rim_diameter + hook_height)
    p7 = d3d.Point2D(0.5 * rim_width, 0.5 * rim_diameter + hook_height)
    p8 = d3d.Point2D(0.5 * rim_width, 0.5 * rim_diameter)
    contour = ClosedRoundedLineSegments2D([p1, p2, p3, p4, p5, p6, p7, p8], {2: 0.003, 5: 0.003})
    return RevolvedProfile(d3d.OYZX, contour, axis_point=d3d.O3D, axis=d3d.Y3D, name=name)


# Brake disk
def brake_disk(
    inner_diameter: float,
    outer_diameter: float,
    brake_width: float,
    number_screws: float,
    screw_diameter: float,
    screwholes_diameter: float,
    name: str = "Brake disk",
):
    bottom_diameter = screw_diameter - 2 * screwholes_diameter
    screw_angle = 2 * math.pi / number_screws
    screw_sector_angle = 3 * 2 * math.atan(screwholes_diameter / screw_diameter)
    remaining_angle = screw_angle - screw_sector_angle
    brake_disk_inner_contours = []
    if remaining_angle > 0:
        p1 = d3d.Point2D(0, 0.5 * bottom_diameter).rotation(d3d.O2D, -0.5 * screw_sector_angle)
        p2 = d3d.Point2D(0, 0.5 * bottom_diameter).rotation(d3d.O2D, 0.5 * screw_sector_angle)
        p3 = d3d.Point2D(0, 0.5 * inner_diameter).rotation(d3d.O2D, 0.5 * screw_sector_angle)
        p4 = d3d.Point2D(0, 0.5 * inner_diameter).rotation(d3d.O2D, screw_angle - 0.5 * screw_sector_angle)
        p5 = d3d.Point2D(0, 0.5 * bottom_diameter).rotation(d3d.O2D, screw_angle - 0.5 * screw_sector_angle)

        a1 = Arc2D(Circle2D.from_center_and_radius(d3d.Point2D(0, 0), 0.5 * bottom_diameter), p1, p2)
        s2 = LineSegment2D(p2, p3)
        a3 = Arc2D(Circle2D.from_center_and_radius(d3d.Point2D(0, 0), 0.5 * inner_diameter), p3, p4)
        s5 = LineSegment2D(p4, p5)

        inner_contour_primitives = []

        for i in range(number_screws):
            inner_contour_primitives.extend(
                [
                    a1.rotation(d3d.O2D, i * screw_angle),
                    s2.rotation(d3d.O2D, i * screw_angle),
                    a3.rotation(d3d.O2D, i * screw_angle),
                    s5.rotation(d3d.O2D, i * screw_angle),
                ]
            )

        brake_disk_inner_contours.append(Contour2D(inner_contour_primitives))

    else:
        brake_disk_inner_contours.append(
            Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, 0), 0.5 * bottom_diameter))
        )

    for i in range(number_screws):
        brake_disk_inner_contours.append(
            Contour2D.from_circle(
                Circle2D.from_center_and_radius(
                    d3d.Point2D(0, 0.5 * screw_diameter).rotation(d3d.O2D, i * 2 * math.pi / number_screws),
                    0.5 * screwholes_diameter,
                )
            )
        )

    return ExtrudedProfile(
        d3d.OZXY,
        Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, 0), 0.5 * outer_diameter)),
        brake_disk_inner_contours,
        brake_width,
        name=name,
    )


def wheel_assembly(
    tyre_size: str,
    rim_width: float,
    bearing_d: float,
    bearing_D: float,
    bearing_B: float,
    bearing_spacing: float,
    disk: ExtrudedProfile,
    disk_offset: float,
    name: str,
):
    """
    Assembly of a wheel: tyre, rim, bearings with their spacer and brake disk.

    The wheel is centered on the origin, its axis being the Y axis. The axle is not part of the wheel.
    """
    width, diameter, rim_diameter = tyre_dimensions(tyre_size)
    wheel_tyre = tyre(rim_diameter, rim_width, diameter, width, tyre_thickness, f"{name} tyre")
    wheel_rim = rim(rim_diameter, rim_width, name=f"{name} rim")
    right_bearing = radial_bearing(bearing_d, bearing_D, bearing_B, name=f"{name} right bearing")
    left_bearing = radial_bearing(bearing_d, bearing_D, bearing_B, name=f"{name} left bearing")
    bearing_spacer = HollowCylinder(
        d3d.OZXY,
        inner_radius=0.5 * bearing_d,
        outer_radius=0.5 * bearing_d + 0.004,
        length=bearing_spacing - bearing_B,
        name=f"{name} bearing spacer",
    )
    return Assembly(
        [wheel_tyre, wheel_rim, right_bearing, bearing_spacer, left_bearing, disk],
        [
            d3d.OXYZ,
            d3d.OXYZ,
            d3d.Frame3D(d3d.Point3D(0, 0.5 * bearing_spacing, 0), d3d.Z3D, d3d.X3D, d3d.Y3D),
            d3d.OXYZ,
            d3d.Frame3D(d3d.Point3D(0, -0.5 * bearing_spacing, 0), d3d.Z3D, d3d.X3D, d3d.Y3D),
            d3d.Frame3D(d3d.Point3D(0, disk_offset, 0), d3d.X3D, d3d.Y3D, d3d.Z3D),
        ],
        name=f"{name} wheel",
    )


front_brake_disk = brake_disk(
    front_brake_disk_inner_diameter,
    front_brake_disk_outer_diameter,
    front_brake_width,
    front_disk_number_screws,
    front_brake_screw_diameter,
    front_disk_screwholes_diameter,
    name="Front brake disk",
)
front_wheel = wheel_assembly(
    front_tyre_size,
    front_rim_width,
    front_bearing_d,
    front_bearing_D,
    front_bearing_B,
    front_bearing_spacing,
    front_brake_disk,
    front_brake_disk_offset,
    "Front",
)
front_axle = Cylinder(d3d.OZXY, 0.5 * front_axle_diameter, tubes_spacing, name="Front wheel axle")

rear_brake_disk = brake_disk(
    rear_brake_disk_inner_diameter,
    rear_brake_disk_outer_diameter,
    rear_brake_width,
    rear_disk_number_screws,
    rear_brake_screw_diameter,
    rear_disk_screwholes_diameter,
    name="Rear brake disk",
)
rear_wheel = wheel_assembly(
    rear_tyre_size,
    rear_rim_width,
    rear_axle_diameter,
    rear_bearing_D,
    rear_bearing_B,
    rear_bearing_spacing,
    rear_brake_disk,
    rear_brake_disk_offset,
    "Rear",
)


def rounded_rectangle(width: float, height: float, radius: float) -> ClosedRoundedLineSegments2D:
    """Rounded rectangle centered on the origin. Its primitives do not depend on its dimensions, for lofts."""
    return ClosedRoundedLineSegments2D(
        [
            d3d.Point2D(-0.5 * width, -0.5 * height),
            d3d.Point2D(0.5 * width, -0.5 * height),
            d3d.Point2D(0.5 * width, 0.5 * height),
            d3d.Point2D(-0.5 * width, 0.5 * height),
        ],
        {0: radius, 1: radius, 2: radius, 3: radius},
    )


def tube_between(start: d3d.Point3D, end: d3d.Point3D, diameter: float, name: str, color=None) -> Cylinder:
    """Cylinder whose axis goes from start to end."""
    axis = end - start
    w = axis.unit_vector()
    u = w.deterministic_unit_normal_vector()
    frame = d3d.Frame3D(0.5 * (start + end), u, w.cross(u), w)
    return Cylinder(frame, 0.5 * diameter, axis.norm(), color=color, name=name)


def y_axis_tube(center: d3d.Point3D, outer_diameter: float, length: float, name: str, inner_diameter: float = 0.0):
    """Tube or cylinder along the Y axis, centered on a point."""
    frame = d3d.Frame3D(center, d3d.Z3D, d3d.X3D, d3d.Y3D)
    if inner_diameter:
        return HollowCylinder(frame, 0.5 * inner_diameter, 0.5 * outer_diameter, length, color=frame_grey, name=name)
    return Cylinder(frame, 0.5 * outer_diameter, length, color=frame_grey, name=name)


## Swingarm, built in the swingarm frame: origin at the pivot, X along the arm toward the rear axle, Z up
def swingarm_arm(side: float, name: str) -> Loft:
    """Arm of the swingarm, its section getting smaller from the pivot to the rear axle. side is 1 (right) or -1."""
    y = 0.5 * side * swingarm_arm_spacing
    abscissas = (0.5 * swingarm_pivot_tube_diameter, 0.5 * swingarm_length, swingarm_length + 0.025)
    return Loft(
        [rounded_rectangle(swingarm_arm_width, height, 0.008) for height in swingarm_arm_heights],
        [d3d.Frame3D(d3d.Point3D(x, y, 0), d3d.Y3D, d3d.Z3D, d3d.X3D) for x in abscissas],
        color=frame_grey,
        name=name,
    )


swingarm_cross_member = ExtrudedProfile(
    d3d.Frame3D(d3d.Point3D(swingarm_cross_member_distance, 0.5 * swingarm_arm_spacing, 0), d3d.X3D, d3d.Z3D, -d3d.Y3D),
    rounded_rectangle(swingarm_cross_member_size, swingarm_cross_member_size, 0.010),
    [],
    swingarm_arm_spacing,
    color=frame_grey,
    name="Swingarm cross member",
)
swingarm_total_width = swingarm_arm_spacing + swingarm_arm_width
swingarm_assembly = Assembly(
    [
        swingarm_arm(1, "Swingarm right arm"),
        swingarm_arm(-1, "Swingarm left arm"),
        y_axis_tube(d3d.O3D, swingarm_pivot_tube_diameter, swingarm_total_width, "Swingarm pivot tube"),
        swingarm_cross_member,
        y_axis_tube(
            d3d.Point3D(shock_lower_mount_distance, 0, shock_lower_mount_height),
            shock_eye_diameter,
            2 * shock_eye_width,
            "Shock lower mount",
        ),
        y_axis_tube(d3d.Point3D(swingarm_length, 0, 0), rear_axle_diameter, swingarm_total_width + 0.02, "Rear axle"),
        rear_wheel,
    ],
    [d3d.OXYZ] * 6 + [d3d.Frame3D(d3d.Point3D(swingarm_length, 0, 0), d3d.X3D, d3d.Y3D, d3d.Z3D)],
    name="Swingarm",
)
# The rear wheel must fit between the arms, with the chain on the left
if 0.5 * swingarm_arm_spacing - 0.5 * swingarm_arm_width < abs(chain_line) + 0.5 * chain_width:
    raise ValueError("The swingarm arms are too close to each other for the rear tyre and the chain.")

## Rear shock, between its mounts on the swingarm and on the frame
shock_axis = (shock_upper_mount - shock_lower_mount).unit_vector()
shock_length = shock_lower_mount.point_distance(shock_upper_mount)


def shock_point(ratio: float) -> d3d.Point3D:
    """Point on the shock axis, from its lower mount (0) to its upper mount (1)."""
    return shock_lower_mount + ratio * shock_length * shock_axis


rear_shock_parts = [
    y_axis_tube(shock_lower_mount, shock_eye_diameter, shock_eye_width, "Shock lower eye", 0.010),
    tube_between(shock_point(0.05), shock_point(0.55), shock_rod_diameter, "Shock rod", color=frame_grey),
    tube_between(shock_point(0.45), shock_point(0.95), shock_body_diameter, "Shock body", color=frame_grey),
    y_axis_tube(shock_upper_mount, shock_eye_diameter, shock_eye_width, "Shock upper eye", 0.010),
]
spring_axis_frame = d3d.Frame3D(
    shock_point(0.5),
    shock_axis.deterministic_unit_normal_vector(),
    shock_axis.cross(shock_axis.deterministic_unit_normal_vector()),
    shock_axis,
)
rear_shock_parts.append(
    HollowCylinder(
        spring_axis_frame,
        0.5 * shock_spring_inner_diameter,
        0.5 * shock_spring_outer_diameter,
        0.6 * shock_length,
        color=spring_red,
        name="Shock spring",
    )
)
rear_shock = Assembly(rear_shock_parts, [d3d.OXYZ] * len(rear_shock_parts), name="Rear shock")

## Fork
# Tubes
left_fork_tube = Cylinder(d3d.OXYZ, 0.5 * tube_diameter, tube_height, name="Left tube").translation(
    -0.5 * tubes_spacing * d3d.Y3D + 0.5 * tube_height * d3d.Z3D
)
right_fork_tube = left_fork_tube.translation(tubes_spacing * d3d.Y3D)
right_fork_tube.name = "Right tube"

# Crowns
c1 = Circle2D.from_center_and_radius(
    d3d.Point2D(-0.5 * tubes_spacing, 0), 0.5 * crown_tube_outer_diameter, is_trigo=False
)
c2 = Circle2D.from_center_and_radius(
    d3d.Point2D(0.5 * tubes_spacing, 0), 0.5 * crown_tube_outer_diameter, is_trigo=False
)
c3 = Circle2D.from_center_and_radius(d3d.Point2D(0, -fork_offset), 0.5 * crown_pivot_outer_diameter, is_trigo=False)

p1 = d3d.Point2D(-0.5 * tubes_spacing, 0.5 * crown_tube_outer_diameter)
p2 = d3d.Point2D(0.5 * tubes_spacing, 0.5 * crown_tube_outer_diameter)
p3 = d3d.Point2D(0.5 * tubes_spacing + 0.5 * crown_tube_outer_diameter, 0)
# p4 = d3d.Point2D(0.5*tubes_spacing, -0.5*crown_tube_outer_diameter)

s1, _ = LineSegment2D.external_circle_tangents(c1, c2)
s2, _ = LineSegment2D.external_circle_tangents(c2, c3)
s3, _ = LineSegment2D.external_circle_tangents(c3, c1)

fork_crown_outer_contour = Contour2D(
    [s1, Arc2D(c2, s1.end, s2.start), s2, Arc2D(c3, s2.end, s3.start), s3, Arc2D(c1, s3.end, s1.start)]
)

lower_fork_crown = ExtrudedProfile(
    d3d.OXYZ,
    fork_crown_outer_contour,
    [
        Contour2D.from_circle(
            Circle2D.from_center_and_radius(d3d.Point2D(-0.5 * tubes_spacing, 0), 0.5 * tube_diameter)
        ),
        Contour2D.from_circle(
            Circle2D.from_center_and_radius(d3d.Point2D(0.5 * tubes_spacing, 0), 0.5 * tube_diameter)
        ),
        Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, -fork_offset), 0.5 * fork_pivot_diameter)),
    ],
    crown_width,
    name="lower crown",
)


upper_fork_crown = lower_fork_crown.copy()
upper_fork_crown.name = "upper crown"

# Handlebar
p1 = d3d.Point3D(-0.5 * handlebar_span, 0, handlebar_offset).rotation(d3d.O3D, d3d.Z3D, handlebar_angle)
p2 = d3d.Point3D(-0.3 * handlebar_span, 0, handlebar_offset).rotation(d3d.O3D, d3d.Z3D, handlebar_angle)
p3 = d3d.Point3D(-0.5 * handlebar_base_width, 0, 0)
p4 = d3d.Point3D(0.5 * handlebar_base_width, 0, 0)
p5 = d3d.Point3D(0.3 * handlebar_span, 0, handlebar_offset).rotation(d3d.O3D, d3d.Z3D, -handlebar_angle)
p6 = d3d.Point3D(0.5 * handlebar_span, 0, handlebar_offset).rotation(d3d.O3D, d3d.Z3D, -handlebar_angle)
handlebar_wire = OpenRoundedLineSegments3D([p1, p2, p3, p4, p5, p6], {1: 0.07, 2: 0.05, 3: 0.05, 4: 0.07})
handlebar = Sweep(
    contour2d=Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.O2D, 0.5 * handlebar_diameter)),
    wire3d=handlebar_wire,
    name="Handlebar",
)

# Fork Frame axle
p1 = d3d.Point2D(-0.005, 0.5 * fork_pivot_inner_diameter)
p2 = d3d.Point2D(-0.005, 0.5 * fork_pivot_diameter + 0.007)
p3 = d3d.Point2D(0, 0.5 * fork_pivot_diameter + 0.007)
p4 = d3d.Point2D(0, 0.5 * fork_pivot_diameter)
p5 = d3d.Point2D(crowns_distance + 0.025, 0.5 * fork_pivot_diameter)
p6 = d3d.Point2D(crowns_distance + 0.025, 0.5 * fork_pivot_inner_diameter)

fork_frame_axle_contour = ClosedPolygon2D([p1, p2, p3, p4, p5, p6])
fork_frame_axle = RevolvedProfile(
    d3d.OZXY, fork_frame_axle_contour, axis_point=d3d.O3D, axis=d3d.Z3D, name="Fork-frame axle"
)
fork_frame_nut = hexnut(fork_pivot_diameter, 0.012)

fork_assembly = Assembly(
    [
        left_fork_tube,
        right_fork_tube,
        front_axle,
        front_wheel,
        upper_fork_crown,
        lower_fork_crown,
        handlebar,
        fork_frame_axle,
        fork_frame_nut,
    ],
    [
        d3d.OXYZ,
        d3d.OXYZ,
        d3d.OXYZ,
        d3d.OXYZ,
        d3d.Frame3D(d3d.Point3D(0, 0, tube_height - crown_width), d3d.Y3D, -d3d.X3D, d3d.Z3D),
        d3d.Frame3D(d3d.Point3D(0, 0, tube_height - crowns_distance - 2 * crown_width), d3d.Y3D, -d3d.X3D, d3d.Z3D),
        d3d.Frame3D(d3d.Point3D(0, 0, tube_height + crown_handlebar_offset), d3d.Y3D, -d3d.X3D, d3d.Z3D),
        d3d.Frame3D(
            d3d.Point3D(fork_offset, 0, tube_height - 2 * crown_width - crowns_distance), d3d.X3D, d3d.Y3D, d3d.Z3D
        ),
        d3d.Frame3D(d3d.Point3D(fork_offset, 0, tube_height), d3d.X3D, d3d.Y3D, d3d.Z3D),
    ],
)


## Engine
def xz_profile_extrusion(profile, y_min: float, y_max: float, inner_contours=None, name: str = "", color=None):
    """Extrusion along the Y axis, between y_min and y_max, of a profile drawn in the XZ plane (2D x is X, y is Z)."""
    if not isinstance(profile, Contour2D):
        profile = ClosedPolygon2D([d3d.Point2D(x, z) for x, z in profile])
    return ExtrudedProfile(
        d3d.Frame3D(d3d.Point3D(0, y_max, 0), d3d.X3D, d3d.Z3D, -d3d.Y3D),
        profile,
        inner_contours or [],
        y_max - y_min,
        color=color,
        name=name,
    )


crankcase_left_side = chain_line - chain_side * (0.5 * chain_width + 0.005)
crankcase = xz_profile_extrusion(
    crankcase_profile, crankcase_left_side, crankcase_right_side, name="Crankcase", color=engine_grey
)


def cylinder_frame(distance: float) -> d3d.Frame3D:
    """Frame on the cylinder axis, at a distance from the crankshaft: w along the axis, u along Y."""
    return d3d.Frame3D(
        crankshaft_center + distance * cylinder_axis, d3d.Y3D, cylinder_axis.cross(d3d.Y3D), cylinder_axis
    )


cylinder_block = Loft(
    [rounded_rectangle(cylinder_block_size, cylinder_block_size, 0.015)] * 2,
    [cylinder_frame(distance) for distance in cylinder_block_distance],
    color=engine_grey,
    name="Cylinder block",
)
cylinder_head = Loft(
    [
        rounded_rectangle(cylinder_head_size, cylinder_head_size, 0.015),
        rounded_rectangle(cylinder_head_size, cylinder_head_size, 0.015),
        rounded_rectangle(0.8 * cylinder_head_size, 0.8 * cylinder_head_size, 0.015),
    ],
    [
        cylinder_frame(cylinder_block_distance[1]),
        cylinder_frame(cylinder_block_distance[1] + 0.7 * cylinder_head_height),
        cylinder_frame(cylinder_block_distance[1] + cylinder_head_height),
    ],
    color=engine_grey,
    name="Cylinder head",
)
engine = Assembly([crankcase, cylinder_block, cylinder_head], [d3d.OXYZ] * 3, name="Engine")


## Chain drive, in the chain plane (y = chain_line)
def belt_contour(center1: d3d.Point2D, radius1: float, center2: d3d.Point2D, radius2: float) -> Contour2D:
    """Contour around two circles, made of their external tangents and arcs."""
    circle1 = Circle2D.from_center_and_radius(center1, radius1, is_trigo=False)
    circle2 = Circle2D.from_center_and_radius(center2, radius2, is_trigo=False)
    tangent1, _ = LineSegment2D.external_circle_tangents(circle1, circle2)
    tangent2, _ = LineSegment2D.external_circle_tangents(circle2, circle1)
    return Contour2D(
        [tangent1, Arc2D(circle2, tangent1.end, tangent2.start), tangent2, Arc2D(circle1, tangent2.end, tangent1.start)]
    )


def sprocket(center: d3d.Point3D, number_teeth: int, bore_diameter: float, name: str) -> ExtrudedProfile:
    """Sprocket with simplified teeth, in the chain plane."""
    radius = sprocket_pitch_radius(number_teeth)
    teeth_points = [
        d3d.Point2D(center.x, center.z)
        + (radius + (0.5 if i % 2 == 0 else -0.5) * sprocket_tooth_height)
        * d3d.Vector2D(math.cos(math.pi * i / number_teeth), math.sin(math.pi * i / number_teeth))
        for i in range(2 * number_teeth)
    ]
    bore = Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(center.x, center.z), 0.5 * bore_diameter))
    return xz_profile_extrusion(
        ClosedPolygon2D(teeth_points),
        chain_line - 0.5 * sprocket_width,
        chain_line + 0.5 * sprocket_width,
        [bore],
        name=name,
        color=steel,
    )


front_sprocket_center2d = d3d.Point2D(front_sprocket_center.x, front_sprocket_center.z)
rear_sprocket_center2d = d3d.Point2D(rear_axle_center.x, rear_axle_center.z)
chain = xz_profile_extrusion(
    belt_contour(
        front_sprocket_center2d,
        front_sprocket_radius + 0.5 * chain_height,
        rear_sprocket_center2d,
        rear_sprocket_radius + 0.5 * chain_height,
    ),
    chain_line - 0.5 * chain_width,
    chain_line + 0.5 * chain_width,
    [
        belt_contour(
            front_sprocket_center2d,
            front_sprocket_radius - 0.5 * chain_height,
            rear_sprocket_center2d,
            rear_sprocket_radius - 0.5 * chain_height,
        )
    ],
    name="Chain",
    color=chain_dark,
)
transmission = Assembly(
    [
        sprocket(front_sprocket_center, front_sprocket_teeth, 0.020, "Front sprocket"),
        sprocket(rear_axle_center, rear_sprocket_teeth, 0.090, "Rear sprocket"),
        chain,
    ],
    [d3d.OXYZ] * 3,
    name="Transmission",
)

# The fork assembly is built with the front axle at its origin and the fork tubes along its Z axis
fork_frame = d3d.XYZ.rotation(d3d.Y3D, caster_angle).to_frame(front_axle_center)

# Frame
frame_pivot_frame = d3d.XYZ.rotation(d3d.Y3D, caster_angle).to_frame(d3d.Point3D(0, 0, 0))
frame_pivot = HollowCylinder(
    frame_pivot_frame,
    inner_radius=0.5 * fork_pivot_diameter,
    outer_radius=0.5 * frame_head_tube_outer_diameter,
    length=crowns_distance,
    color=frame_grey,
    name="Steering head tube",
)


def spar_frames(points: list[tuple[float, float]], half_spacings: list[float], side: float) -> list[d3d.Frame3D]:
    """
    Frames of the spar sections: their w vector is tangent to the spar, their u vector is close to the Y axis.

    :param side: 1 for the right spar, -1 for the left one.
    """
    centers = [d3d.Point3D(x, side * y, z) for (x, z), y in zip(points, half_spacings)]
    frames = []
    for i, center in enumerate(centers):
        w = (centers[min(i + 1, len(centers) - 1)] - centers[max(i - 1, 0)]).unit_vector()
        u = (d3d.Y3D - d3d.Y3D.dot(w) * w).unit_vector()
        frames.append(d3d.Frame3D(center, u, w.cross(u), w))
    return frames


def frame_spar(side: float, name: str) -> Loft:
    return Loft(
        [rounded_rectangle(width, height, 0.008) for width, height in spar_sections],
        spar_frames(spar_points, spar_half_spacings, side),
        color=frame_grey,
        name=name,
    )


def subframe_tube(points: list[tuple[float, float]], y: float, name: str):
    points3d = [d3d.Point3D(x, y, z) for x, z in points]
    tube_section = Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.O2D, 0.5 * subframe_tube_diameter))
    if len(points3d) == 2:
        return tube_between(points3d[0], points3d[1], subframe_tube_diameter, name, color=frame_grey)
    wire = OpenRoundedLineSegments3D(points3d, {i: 0.15 for i in range(1, len(points3d) - 1)})
    return Sweep(tube_section, wire, color=frame_grey, name=name)


rail_end = d3d.Point3D(subframe_rail_points[-1][0], 0, subframe_rail_points[-1][1])
frame_parts = [
    frame_spar(1, "Right spar"),
    frame_spar(-1, "Left spar"),
    subframe_tube(subframe_rail_points, subframe_rail_half_spacing, "Right subframe rail"),
    subframe_tube(subframe_rail_points, -subframe_rail_half_spacing, "Left subframe rail"),
    subframe_tube(subframe_stay_points, subframe_rail_half_spacing, "Right subframe stay"),
    subframe_tube(subframe_stay_points, -subframe_rail_half_spacing, "Left subframe stay"),
    y_axis_tube(rail_end, subframe_tube_diameter, 2 * subframe_rail_half_spacing, "Subframe rear cross tube"),
    y_axis_tube(
        shock_upper_mount, subframe_tube_diameter, 2 * subframe_rail_half_spacing, "Shock upper mount cross tube"
    ),
    y_axis_tube(
        swingarm_pivot,
        0.5 * swingarm_pivot_tube_diameter,
        2 * spar_half_spacings[-1] + spar_sections[-1][0] + 0.02,
        "Swingarm pivot shaft",
    ),
]
frame = Assembly(
    [frame_pivot, *frame_parts],
    [d3d.Frame3D(steering_head_center, d3d.X3D, d3d.Y3D, d3d.Z3D)] + [d3d.OXYZ] * len(frame_parts),
    name="Frame",
)

motorcycle = Assembly(
    [fork_assembly, frame, swingarm_assembly, rear_shock, engine, transmission],
    [fork_frame, d3d.OXYZ, swingarm_frame, d3d.OXYZ, d3d.OXYZ, d3d.OXYZ],
    name="Motorcycle",
)

# ======================================================================================================================
# Checks
# ======================================================================================================================

print("Hardpoints (x, z) in mm:")
for hardpoint_name, hardpoint in [
    ("front axle", front_axle_center),
    ("steering axis on the ground", steering_axis_ground_point),
    ("steering head", steering_head_center),
    ("swingarm pivot", swingarm_pivot),
    ("rear axle", rear_axle_center),
    ("shock lower mount", shock_lower_mount),
    ("shock upper mount", shock_upper_mount),
    ("crankshaft", crankshaft_center),
    ("front sprocket", front_sprocket_center),
]:
    print(f"  {hardpoint_name:<28} {1000 * hardpoint.x:7.1f} {1000 * hardpoint.z:7.1f}")
print(f"Fork offset: {1000 * fork_offset:.1f} mm, tyre to lower crown clearance: {1000 * tyre_crown_clearance:.0f} mm")
print(f"Engine: {1e6 * math.pi / 4 * engine_bore**2 * engine_stroke:.1f} cm3")
print(f"Chain: {chain_links:.1f} links, {math.ceil(chain_links / 2) * 2} with an even number")
print(
    f"Rear shock length (eye to eye): {1000 * shock_length:.0f} mm, swingarm width: {1000 * swingarm_total_width:.0f} mm"
)

# Overall dimensions of the model, compared to the MT-125 ones. They are computed on the meshes of the parts, as the
# bounding boxes of some faces (toroidal faces of the tyres) are underestimated.
motorcycle_meshes = d3d.core.VolumeModel([motorcycle]).to_mesh_list()
motorcycle_vertices = np.concatenate([mesh.vertices for mesh in motorcycle_meshes])
model_min, model_max = motorcycle_vertices.min(axis=0), motorcycle_vertices.max(axis=0)
print("Overall dimensions (model / MT-125) in mm:")
for dimension_name, axis, target_value in [("length", 0, target_length), ("width", 1, target_width)]:
    print(f"  {dimension_name:<7} {1000 * (model_max[axis] - model_min[axis]):6.0f} / {1000 * target_value:4.0f}")
print(f"  {'height':<7} {1000 * model_max[2]:6.0f} / {1000 * target_height:4.0f}")
# Ground clearance: lowest point of the parts that are not wheel parts
wheel_part_names = {component.name for wheel in (front_wheel, rear_wheel) for component in wheel.components}
ground_clearance = min(mesh.vertices[:, 2].min() for mesh in motorcycle_meshes if mesh.name not in wheel_part_names)
print(f"Ground clearance (model / MT-125): {1000 * ground_clearance:.0f} / {1000 * target_ground_clearance:.0f} mm")


# Sides of the chain and of the rear brake, from the rider's point of view (the rider faces -X, Z being up)
def rider_side(part_name: str) -> str:
    part_center = np.mean([mesh.vertices.mean(axis=0) for mesh in motorcycle_meshes if mesh.name == part_name], axis=0)
    return "left" if d3d.Vector3D(*part_center).dot(d3d.Z3D.cross(-d3d.X3D)) > 0 else "right"


print(f"Chain on the {rider_side('Chain')} side, rear brake disk on the {rider_side('Rear brake disk')} side")
if (rider_side("Chain"), rider_side("Rear brake disk")) != ("left", "right"):
    raise ValueError("The chain must be on the left side and the rear brake on the right side.")

primitives = [ground, motorcycle]

scene = d3d.core.VolumeModel(primitives, name="Motorcycle")

scene.babylonjs()

scene.to_step("motorcycle")
