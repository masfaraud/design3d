#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

"""
import math
import time

import design3d as d3d
from design3d import faces, edges, wires, surfaces, shells

time_before = time.time()

number_points = 50

poly_1 = wires.ClosedPolygon3D([d3d.Point3D(-0.3, 0.05, -0.20),
                                d3d.Point3D(0, 0.25, -0.20),
                                d3d.Point3D(0.25, 0.1, -0.20),
                                d3d.Point3D(0.2, -0.15, -0.20),
                                d3d.Point3D(-0.2, -0.12, -0.20)])

length_poly_11 = poly_1.length()

points_poly_11 = [poly_1.point_at_abscissa(k*length_poly_11/(number_points)) for k in range(number_points)]

new_poly_11 = wires.ClosedPolygon3D(points_poly_11)

new_poly_12 = new_poly_11.translation(0.3*d3d.Z3D).rotation(d3d.O3D, d3d.Z3D, math.pi/2)

new_poly_13 = new_poly_12.translation(0.05*d3d.Z3D)

new_poly_14 = new_poly_13.translation(0.2*d3d.Z3D).rotation(d3d.O3D, d3d.Z3D, math.pi/4)
# faces1 = [faces.Triangle3D(*points)
#           for points in new_poly_11.sewing(new_poly_12,d3d.X3D, d3d.Y3D)]
# d3d.core.VolumeModel(faces1).babylonjs()
faces1 = [faces.Triangle3D(*points)
          for points in new_poly_11.sewing(new_poly_12,d3d.X3D, d3d.Y3D)] + \
         [faces.Triangle3D(*points)
          for points in
          new_poly_12.sewing(new_poly_13, d3d.X3D, d3d.Y3D)] + \
         [faces.Triangle3D(*points)
          for points in
          new_poly_13.sewing(new_poly_14, d3d.X3D, d3d.Y3D)]

# # faces1 = [faces.Triangle3D(trio[0], trio[1], trio[2]) for trio in points_triangles_1]
#
plane3d_1 = surfaces.Plane3D.from_plane_vectors(-0.2*d3d.Z3D.to_point(), d3d.X3D, d3d.Y3D)
surf2d_1 = surfaces.Surface2D(new_poly_11.to_2d(d3d.O3D, d3d.X3D, d3d.Y3D),[])

plane3d_2 = surfaces.Plane3D.from_plane_vectors(0.35*d3d.Z3D.to_point(), d3d.X3D, d3d.Y3D)
surf2d_2 = surfaces.Surface2D(new_poly_14.to_2d(d3d.O3D, d3d.X3D, d3d.Y3D),[])
faces1 += [faces.PlaneFace3D(plane3d_1, surf2d_1), faces.PlaneFace3D(plane3d_2, surf2d_2)]

shell1 = shells.ClosedShell3D(faces1)

poly_2 = wires.ClosedPolygon3D([d3d.Point3D(-0.10, 0.05, 0),
                                d3d.Point3D(-0.07, 0.05, 0.05),
                                d3d.Point3D(0, 0.05, 0.10),
                                d3d.Point3D(0.05, 0.05, 0.07),
                                d3d.Point3D(0.10, 0.05, 0)])

length_poly_2 = poly_2.length()

points_poly_2 = [poly_2.point_at_abscissa(k*length_poly_2/(number_points)) for k in range(number_points)]

new_poly_21 = wires.ClosedPolygon3D(points_poly_2)
new_poly_22 = new_poly_21.translation(0.1*d3d.Y3D).rotation(d3d.O3D, d3d.Y3D, math.pi/2)
new_poly_23 = new_poly_22.translation(0.05*d3d.Y3D)
new_poly_24 = new_poly_23.translation(0.2*d3d.Y3D).rotation(d3d.O3D, d3d.Y3D, math.pi/4)
faces2 = [faces.Triangle3D(*points)
          for points in new_poly_21.sewing(new_poly_22, d3d.X3D, d3d.Z3D)] + \
         [faces.Triangle3D(*points)
          for points in
          new_poly_23.sewing(new_poly_22, d3d.X3D, d3d.Z3D)] + \
         [faces.Triangle3D(*points)
          for points in
          new_poly_23.sewing(new_poly_24, d3d.X3D, d3d.Z3D)]

# faces2 = [faces.Triangle3D(trio[0], trio[1], trio[2]) for trio in points_triangles_2]

plane3d_3 = surfaces.Plane3D.from_plane_vectors(0.05*d3d.Y3D.to_point(), d3d.Z3D, d3d.X3D)
surf2d_3 = surfaces.Surface2D(new_poly_21.to_2d(d3d.O3D, d3d.Z3D, d3d.X3D),[])

plane3d_4 = surfaces.Plane3D.from_plane_vectors(0.4*d3d.Y3D.to_point(), d3d.Z3D, d3d.X3D)
surf2d_4 = surfaces.Surface2D(new_poly_24.to_2d(d3d.O3D, d3d.Z3D, d3d.X3D),[])
faces2 += [faces.PlaneFace3D(plane3d_3, surf2d_3), faces.PlaneFace3D(plane3d_4, surf2d_4)]

shell2 = shells.ClosedShell3D(faces2)
# shell2.color=(1, 0.1, 0.1)
# shell2.alpha = 0.6
# shell2.babylonjs()
new_box = shell1.union(shell2)
subtract_to_closed_shell = shell1.subtract_to_closed_shell(shell2)
# new_box = shell1.intersection(shell2)
for shell in [new_box, subtract_to_closed_shell]:
    shell[0].color = (1, 0.1, 0.1)
    shell[0].alpha = 0.6
    shell[0].babylonjs()


time_after = time.time()

if (time_after-time_before) < 60:
    print('run time in seconds:', (time_after-time_before))
else:
    print('run time in minutes:', (time_after-time_before) / 60)
