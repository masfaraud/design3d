import math

import matplotlib.pyplot as plt

import design3d as d3d
from design3d.core import Assembly, EdgeStyle
from design3d.curves import Circle2D
from design3d.edges import Arc2D, FullArc2D, LineSegment2D
from design3d.faces import PlaneFace3D
from design3d.primitives2d import ClosedRoundedLineSegments2D
from design3d.primitives3d import (
    Cylinder,
    ExtrudedProfile,
    HollowCylinder,
    OpenRoundedLineSegments3D,
    RevolvedProfile,
    Sweep,
)
from design3d.surfaces import Plane3D
from design3d.wires import ClosedPolygon2D, Contour2D

wheelbase = 1.5

# Tyres
tyre_diameter = 0.5918
tyre_thickness = 0.008
front_tyre_width = 0.100
front_rim_width = 0.06858
rim_diameter = 17 * 0.0254

# rear_tyre_width =


# Wheels

# Brake disks
front_brake_disk_outer_diameter = 0.292
front_brake_disk_inner_diameter = 0.250
front_brake_screw_diameter = 0.220
front_disk_number_screws = 6
front_disk_screwholes_diameter = 0.012
front_brake_disk_offset = -0.050
front_brake_width = 0.0045


# Fork
tube_diameter = 0.041
fork_offset = 0.035
front_axle_diameter = 0.015
crown_width = 0.020
crown_tube_outer_diameter = tube_diameter + 0.012
crowns_distance = 0.170
tyre_width_margin = 0.015
tubes_spacing = tube_diameter + front_tyre_width + 2 * tyre_width_margin
fork_pivot_diameter = 0.030
fork_pivot_inner_diameter = 0.026
crown_pivot_outer_diameter = fork_pivot_diameter + 0.012
tyre_crown_clearance = 0.035

# Wheel bearings
front_bearing_d = front_axle_diameter
front_bearing_D = 0.042
front_bearing_B = 0.013
front_bearing_spacing = 0.090

# Handlebar
crown_handlebar_offset = 0.050
handlebar_diameter = 0.028
handlebar_span = 0.650
handlebar_angle = math.radians(15)
handlebar_offset = 0.045
handlebar_base_width = 0.150

# Computed
tube_height = 0.5 * tyre_diameter + crowns_distance + tyre_crown_clearance + 2 * crown_width


# Arm
arm_length = 0.7
caster_angle = math.radians(26.5)

# Colors
tyre_black = (0.15, 0.15, 0.15)
asphalt = (112 / 256, 110 / 256, 106 / 256)

## End of data

# Ground
ground_plane = Plane3D(d3d.OXYZ)
ground = PlaneFace3D.from_surface_rectangular_cut(ground_plane, -0.5, 1.5, -0.5, 0.5)
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
    delta = 0.5 * (D - d)
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


# Wheels
front_tyre = tyre(rim_diameter, front_rim_width, tyre_diameter, front_tyre_width, tyre_thickness, "front_tyre")
front_axle = Cylinder(d3d.OZXY, 0.5 * front_axle_diameter, tubes_spacing, name="Front wheel axle")
front_rim = rim(rim_diameter, front_rim_width, name="Front rim")


# Brake disk
def brake_disk(
    inner_diameter: float,
    outer_diameter: float,
    brake_width: float,
    number_screws: float,
    screw_diameter: float,
    screwholes_diameter: float,
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
        name="Front brake disk",
    )


front_brake_disk = brake_disk(
    front_brake_disk_inner_diameter,
    front_brake_disk_outer_diameter,
    front_brake_width,
    front_disk_number_screws,
    front_brake_screw_diameter,
    front_disk_screwholes_diameter,
)

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

left_front_bearing = radial_bearing(
    front_bearing_d,
    front_bearing_D,
    front_bearing_B,
)
right_front_bearing = radial_bearing(front_bearing_d, front_bearing_D, front_bearing_B)
front_bearing_spacer = HollowCylinder(
    d3d.OZXY,
    inner_radius=0.5 * front_bearing_d,
    outer_radius=0.5 * front_bearing_d + 0.004,
    length=front_bearing_spacing - front_bearing_B,
    name="Front bearing spacer",
)

fork_assembly = Assembly(
    [
        left_fork_tube,
        right_fork_tube,
        front_axle,
        left_front_bearing,
        front_bearing_spacer,
        right_front_bearing,
        front_tyre,
        front_rim,
        front_brake_disk,
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
        d3d.Frame3D(d3d.Point3D(0, -0.5 * front_bearing_spacing, 0), d3d.Z3D, d3d.X3D, d3d.Y3D),
        d3d.OXYZ,
        d3d.Frame3D(d3d.Point3D(0, 0.5 * front_bearing_spacing, 0), d3d.Z3D, d3d.X3D, d3d.Y3D),
        d3d.OXYZ,
        d3d.OXYZ,
        d3d.Frame3D(d3d.Point3D(0, front_brake_disk_offset, 0), d3d.X3D, d3d.Y3D, d3d.Z3D),
        d3d.Frame3D(d3d.Point3D(0, 0, tube_height - crown_width), d3d.Y3D, -d3d.X3D, d3d.Z3D),
        d3d.Frame3D(d3d.Point3D(0, 0, tube_height - crowns_distance - 2 * crown_width), d3d.Y3D, -d3d.X3D, d3d.Z3D),
        d3d.Frame3D(d3d.Point3D(0, 0, tube_height + crown_handlebar_offset), d3d.Y3D, -d3d.X3D, d3d.Z3D),
        d3d.Frame3D(
            d3d.Point3D(fork_offset, 0, tube_height - 2 * crown_width - crowns_distance), d3d.X3D, d3d.Y3D, d3d.Z3D
        ),
        d3d.Frame3D(d3d.Point3D(fork_offset, 0, tube_height), d3d.X3D, d3d.Y3D, d3d.Z3D),
    ],
)


fork_frame = d3d.XYZ.rotation(d3d.Y3D, caster_angle).to_frame(d3d.Point3D(0, 0, 0.5 * tyre_diameter))

# Frame
frame_pivot_frame = d3d.XYZ.rotation(d3d.Y3D, caster_angle).to_frame(d3d.Point3D(0, 0, 0))
frame_pivot = HollowCylinder(
    frame_pivot_frame,
    inner_radius=0.5 * fork_pivot_diameter,
    outer_radius=0.5 * fork_pivot_diameter + 0.008,
    length=crowns_distance,
    name="Frame pivot",
)

frame = frame_pivot
frame_frame = d3d.Frame3D(
    (
        d3d.Point3D(fork_offset, 0, tube_height - 0.5 * crowns_distance - crown_width).rotation(
            d3d.O3D, d3d.Y3D, caster_angle
        )
        + 0.5 * tyre_diameter * d3d.Z3D
    ).to_point(),
    d3d.X3D,
    d3d.Y3D,
    d3d.Z3D,
)

motorcycle = Assembly([fork_assembly, frame], [fork_frame, frame_frame])

primitives = [ground, motorcycle]

scene = d3d.core.VolumeModel(primitives, name="Motorcycle")

scene.babylonjs()

scene.to_step("motorcycle")
