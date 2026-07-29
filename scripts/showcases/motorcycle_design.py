import math

import matplotlib.pyplot as plt

import design3d as d3d
from design3d.core import Assembly, EdgeStyle
from design3d.curves import Circle2D
from design3d.edges import Arc2D, FullArc2D, LineSegment2D
from design3d.faces import PlaneFace3D
from design3d.primitives2d import ClosedRoundedLineSegments2D
from design3d.primitives3d import Cylinder, ExtrudedProfile, HollowCylinder, RevolvedProfile
from design3d.surfaces import Plane3D
from design3d.wires import ClosedPolygon2D, Contour2D

wheelbase = 1.5

# Tyres
tyre_diameter = 0.591
tyre_thickness = 0.008
front_tyre_width = 0.12
front_rim_width = 0.1
rim_diameter = 16*0.0254

# rear_tyre_width = 


# Wheels

# Brake disks
front_brake_disk_outer_diameter = 0.292
front_brake_disk_inner_diameter = 0.250
front_brake_screw_diameter = 0.220
front_disk_number_screws = 6
front_disk_screwholes_diameter = 0.012
front_brake_disk_offset = -0.050
front_brake_width = 0.012


# Fork
tube_diameter = 0.06
tube_height = 0.50
fork_offset = 0.045
front_axle_diameter = 0.020
crown_width = 0.010
crown_tube_outer_diameter = tube_diameter+0.012
crown_height = 0.200
tyre_width_margin = 0.015
tubes_spacing = tube_diameter + front_tyre_width + 2*tyre_width_margin
fork_pivot_diameter = 0.040
fork_pivot_inner_diameter = 0.037
crown_pivot_outer_diameter = fork_pivot_diameter+0.012

# Arm
arm_length = 0.7
caster_angle = math.radians(15)

# Colors
tyre_black = (0.15, 0.15, 0.15)

## End of data

# Ground
ground_plane = Plane3D(d3d.OXYZ, name="Ground")
ground = PlaneFace3D.from_surface_rectangular_cut(ground_plane, -1, 2, -1, 1)

# Wheels

p1 = d3d.Point2D(-0.5*front_rim_width, 0.5*rim_diameter)
p2 = d3d.Point2D(-0.5*front_rim_width, 0.5*rim_diameter + 0.25*(tyre_diameter-rim_diameter-front_tyre_width))
p3 = d3d.Point2D(-0.5*front_tyre_width, 0.5*(tyre_diameter-front_tyre_width))
p4 = d3d.Point2D(0.5*front_tyre_width, 0.5*(tyre_diameter-front_tyre_width))
p5 = d3d.Point2D(0.5*front_rim_width, 0.5*rim_diameter + 0.25*(tyre_diameter-rim_diameter-front_tyre_width))
p6 = d3d.Point2D(0.5*front_rim_width, 0.5*rim_diameter)
p7 = p6 - tyre_thickness*d3d.X3D
p8 = p5 - tyre_thickness*d3d.X3D
p9 = p4 - tyre_thickness*d3d.X3D
p10 = p3 + tyre_thickness*d3d.X3D
p11 = p2 + tyre_thickness*d3d.X3D
p12 = p1 + tyre_thickness*d3d.X3D

front_tyre_contour = Contour2D([
    LineSegment2D(p1, p2), LineSegment2D(p2, p3),
    Arc2D(Circle2D.from_center_and_radius(d3d.Point2D(0, 0.5*(tyre_diameter-front_tyre_width)), 0.5*front_tyre_width, is_trigo=False), p3, p4),
    LineSegment2D(p4, p5), LineSegment2D(p5, p6), LineSegment2D(p6, p7), LineSegment2D(p7, p8), LineSegment2D(p8, p9),
    Arc2D(Circle2D.from_center_and_radius(d3d.Point2D(0, 0.5*(tyre_diameter-front_tyre_width)), 0.5*front_tyre_width-tyre_thickness, is_trigo=True), p9, p10),
    LineSegment2D(p10, p11), LineSegment2D(p11, p12), LineSegment2D(p12, p1)
])
# front_tyre = HollowCylinder(d3d.OZXY, 0.5*rim_diameter, 0.5*tyre_diameter, front_tyre_width, name="Front tyre")
front_tyre = RevolvedProfile(d3d.OYZX, front_tyre_contour, axis_point=d3d.O3D, axis=d3d.Y3D, color=tyre_black)
front_axle = Cylinder(d3d.OZXY, 0.5*front_axle_diameter, tubes_spacing)

# Brake disk
front_brake_disk_inner_contours = [Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, 0), 0.5*front_brake_screw_diameter - front_disk_screwholes_diameter))]
for i in range(front_disk_number_screws):
    front_brake_disk_inner_contours.append(Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, 0.5*front_brake_screw_diameter).rotation(d3d.O2D, i*2*math.pi/front_disk_number_screws), 0.5*front_disk_screwholes_diameter)))

front_brake_disk = ExtrudedProfile(d3d.OZXY, Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, 0), 0.5*front_brake_disk_outer_diameter)), 
                                   front_brake_disk_inner_contours, 
                                   front_brake_width)

## Fork
# Tubes
left_fork_tube = Cylinder(d3d.OXYZ, 0.5*tube_diameter, tube_height).translation(-0.5*tubes_spacing*d3d.Y3D+0.5*tube_height*d3d.Z3D)
right_fork_tube = left_fork_tube.translation(tubes_spacing*d3d.Y3D)

# Crowns
c1 = Circle2D.from_center_and_radius(d3d.Point2D(-0.5*tubes_spacing, 0), 0.5*crown_tube_outer_diameter, is_trigo=False)
c2 = Circle2D.from_center_and_radius(d3d.Point2D(0.5*tubes_spacing, 0), 0.5*crown_tube_outer_diameter, is_trigo=False)
c3 = Circle2D.from_center_and_radius(d3d.Point2D(0, -fork_offset), 0.5*crown_pivot_outer_diameter, is_trigo=False)

p1 = d3d.Point2D(-0.5*tubes_spacing, 0.5*crown_tube_outer_diameter)
p2 = d3d.Point2D(0.5*tubes_spacing, 0.5*crown_tube_outer_diameter)
p3 = d3d.Point2D(0.5*tubes_spacing+0.5*crown_tube_outer_diameter, 0)
# p4 = d3d.Point2D(0.5*tubes_spacing, -0.5*crown_tube_outer_diameter)

s1, _ = LineSegment2D.external_circle_tangents(c1, c2)
s2, _ = LineSegment2D.external_circle_tangents(c2, c3)
s3, _ = LineSegment2D.external_circle_tangents(c3, c1)

fork_crown_outer_contour = Contour2D([s1, Arc2D(c2, s1.end, s2.start), s2, Arc2D(c3, s2.end, s3.start), s3, Arc2D(c1, s3.end, s1.start)
                                      ])

lower_fork_crown = ExtrudedProfile(d3d.OXYZ, fork_crown_outer_contour,
                                   [Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(-0.5*tubes_spacing, 0), 0.5*tube_diameter)),
                                    Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0.5*tubes_spacing, 0), 0.5*tube_diameter)),
                                    Contour2D.from_circle(Circle2D.from_center_and_radius(d3d.Point2D(0, -fork_offset), 0.5*fork_pivot_diameter))],
                                   crown_width, name='lower crown')


upper_fork_crown = lower_fork_crown.copy()
upper_fork_crown.name = "upper crown"

# Fork Frame axle
p1 = d3d.Point2D(-0.005, 0.5*fork_pivot_inner_diameter)
p2 = d3d.Point2D(-0.005, 0.5*fork_pivot_diameter+0.007)
p3 = d3d.Point2D(0, 0.5*fork_pivot_diameter+0.007)
p4 = d3d.Point2D(0, 0.5*fork_pivot_diameter)
p5 = d3d.Point2D(crown_height+0.025, 0.5*fork_pivot_diameter)
p6 = d3d.Point2D(crown_height+0.025, 0.5*fork_pivot_inner_diameter)

fork_frame_axle_contour = ClosedPolygon2D([p1, p2, p3, p4, p5, p6])
fork_frame_axle = RevolvedProfile(d3d.OZXY, fork_frame_axle_contour, axis_point=d3d.O3D, axis=d3d.Z3D)

fork_assembly = Assembly([left_fork_tube, right_fork_tube, front_axle, front_tyre, front_brake_disk, lower_fork_crown, upper_fork_crown, fork_frame_axle],
                         [d3d.OXYZ, d3d.OXYZ, d3d.OXYZ, d3d.OXYZ,
                          d3d.Frame3D(d3d.Point3D(0, front_brake_disk_offset, 0), d3d.X3D, d3d.Y3D, d3d.Z3D),
                          d3d.Frame3D(d3d.Point3D(0, 0, tube_height), d3d.Y3D, -d3d.X3D, d3d.Z3D),
                          d3d.Frame3D(d3d.Point3D(0, 0, tube_height-crown_height), d3d.Y3D, -d3d.X3D, d3d.Z3D),
                          d3d.Frame3D(d3d.Point3D(fork_offset, 0, tube_height-crown_height), d3d.X3D, d3d.Y3D, d3d.Z3D)]
                          )



fork_frame = d3d.XYZ.rotation(d3d.Y3D, caster_angle).to_frame(d3d.Point3D(0, 0, 0.5*tyre_diameter))

motorcycle = Assembly([fork_assembly],
                         [fork_frame])

primitives = [ground, motorcycle]

scene = d3d.core.VolumeModel(primitives, name='Motorcycle')

scene.babylonjs()

plt.show()
