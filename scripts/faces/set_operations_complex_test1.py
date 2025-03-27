import math

import design3d as d3d
import design3d.faces as d3df
import design3d.primitives3d as primitives3D
import design3d.wires as d3dw
from design3d import surfaces, shells

poly1_vol1 = d3dw.ClosedPolygon3D([d3d.Point3D(-0.1, -0.05, 0),
                                  d3d.Point3D(-0.15, 0.1, 0),
                                  d3d.Point3D(0.05, 0.2, 0),
                                  d3d.Point3D(0.12, 0.15, 0),
                                  d3d.Point3D(0.1, -0.02, 0)])

poly2_vol1 = poly1_vol1.rotation(d3d.O3D, d3d.Z3D, math.pi).translation(0.2*d3d.Z3D)
poly3_vol1 = poly2_vol1.rotation(d3d.O3D, d3d.Z3D, math.pi/8).translation(0.1*(d3d.Z3D+d3d.X3D+d3d.Y3D))
#
faces = [d3df.Triangle3D(*points)
          for points in poly1_vol1.sewing(poly2_vol1, d3d.X3D, d3d.Y3D)] + \
        [d3df.Triangle3D(*points)
         for points in poly2_vol1.sewing(poly3_vol1, d3d.X3D, d3d.Y3D)]

# faces = [d3df.Triangle3D(trio[0], trio[1], trio[2]) for trio in point_triangles]

plane3d_1 = surfaces.Plane3D.from_plane_vectors(d3d.O3D, d3d.X3D, d3d.Y3D)
surf2d_1 = surfaces.Surface2D(poly1_vol1.to_2d(d3d.O3D, d3d.X3D, d3d.Y3D),[])

plane3d_2 = surfaces.Plane3D.from_plane_vectors(0.3*d3d.Z3D.to_point(), d3d.X3D, d3d.Y3D)
surf2d_2 = surfaces.Surface2D(poly3_vol1.to_2d(d3d.O3D, d3d.X3D, d3d.Y3D),[])
faces += [d3df.PlaneFace3D(plane3d_1, surf2d_1), d3df.PlaneFace3D(plane3d_2, surf2d_2)]

shell1 = shells.ClosedShell3D(faces)
shell1.color = (0.1, 1, 0.1)
shell1.alpha = 0.4
# shell1.babylonjs()
#
poly1_vol2 = d3dw.ClosedPolygon3D([d3d.Point3D(-0.1, -0.1, -0.2),
                                  d3d.Point3D(-0.15, -0.1, -0.05),
                                  d3d.Point3D(0.05, -0.1, 0.2),
                                  d3d.Point3D(0.12, -0.1, 0.05),
                                  d3d.Point3D(0.1, -0.1, -0.02)])


poly2_vol2 = poly1_vol2.rotation(d3d.O3D, d3d.Y3D, math.pi/2).translation(0.02*d3d.Y3D)
poly3_vol2 = poly2_vol2.rotation(d3d.O3D, d3d.Y3D, math.pi/8).translation(0.1*(d3d.Z3D+d3d.X3D+d3d.Y3D))
poly4_vol2 = poly3_vol2.rotation(d3d.O3D, d3d.Y3D, math.pi/4).translation(0.05*d3d.Y3D)
poly5_vol2 = poly4_vol2.rotation(d3d.O3D, d3d.Y3D, math.pi/10).translation(0.2*d3d.Y3D)

faces_2 = [d3df.Triangle3D(*points)
           for points in poly1_vol2.sewing(poly2_vol2, d3d.X3D, d3d.Z3D)] + \
          [d3df.Triangle3D(*points)
           for points in poly2_vol2.sewing(poly3_vol2, d3d.X3D, d3d.Z3D)] + \
          [d3df.Triangle3D(*points)
           for points in poly3_vol2.sewing(poly4_vol2, d3d.X3D, d3d.Z3D)] + \
          [d3df.Triangle3D(*points)
           for points in poly4_vol2.sewing(poly5_vol2, d3d.X3D, d3d.Z3D)]

# faces_2 = [d3df.Triangle3D(trio[0], trio[1], trio[2]) for trio in point_triangles_2]

plane3d_3 = surfaces.Plane3D.from_plane_vectors(-0.1*d3d.Y3D.to_point(), d3d.X3D, d3d.Z3D)
surf2d_3 = surfaces.Surface2D(poly1_vol2.to_2d(d3d.O3D, d3d.X3D, d3d.Z3D),[])

plane3d_4 = surfaces.Plane3D.from_plane_vectors(0.27*d3d.Y3D.to_point(), d3d.X3D, d3d.Z3D)
surf2d_4 = surfaces.Surface2D(poly5_vol2.to_2d(d3d.O3D, d3d.X3D, d3d.Z3D),[])
faces_2 += [d3df.PlaneFace3D(plane3d_3, surf2d_3), d3df.PlaneFace3D(plane3d_4, surf2d_4)]


shell2 = shells.ClosedShell3D(faces_2)
union_box = shell1.union(shell2)
subtraction_box = shell1.subtract(shell2)
subtraction_closedbox = shell1.subtract_to_closed_shell(shell2)
intersection_box = shell1.intersection(shell2)

for new_box in [union_box, subtraction_box, subtraction_closedbox, intersection_box]:
    for shell in new_box:
        shell.color = (1, 0.1, 0.1)
        shell.alpha = 0.6
    d3d.core.VolumeModel(new_box + [shell1, shell2]).babylonjs()
