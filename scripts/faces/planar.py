import design3d
import design3d.edges
import design3d.faces
import design3d.wires
from design3d import faces, surfaces
from design3d.core import EdgeStyle

p1 = design3d.Point3D(0.15, 0.48, 0.5)
p2 = design3d.Point3D(0.15, 0.1, 0.5)

p1s = design3d.Point2D(0, 0)
p2s = design3d.Point2D(0.1, 0)
p3s = design3d.Point2D(0.2, 0.1)
p4s = design3d.Point2D(-0.01, 0.05)
surface2d = surfaces.Surface2D(design3d.wires.ClosedPolygon2D([p1s, p2s, p3s, p4s]), [])

u = design3d.Vector3D(0.1, 0.7, -0.5)
u = u.unit_vector()
v = u.deterministic_unit_normal_vector()
w = u.cross(v)
plane = surfaces.Plane3D(frame=design3d.Frame3D(0.1*design3d.X3D, u, v, w))
face = design3d.faces.PlaneFace3D(plane, surface2d)

ax = face.plot()
p1.plot(ax=ax, color='b')
p2.plot(ax=ax, color='g')

l1 = design3d.edges.LineSegment3D(p1, p1+w)
l2 = design3d.edges.LineSegment3D(p2, p2+w)

l1.plot(ax=ax, edge_style = EdgeStyle(color='b'))
l2.plot(ax=ax, edge_style = EdgeStyle(color='g'))

i1 = face.linesegment_intersections(l1)
if i1:
    i1[0].plot(ax=ax, color='r')

i2 = face.linesegment_intersections(l2)
if i2:
    i2[0].plot(ax=ax, color='r')

plane_inter_1 = plane.linesegment_intersections(l1)
if plane_inter_1:
    plane_inter_1[0].plot(ax=ax, color='b')
plane_inter_2 = plane.linesegment_intersections(l2)
if plane_inter_2:
    plane_inter_2[0].plot(ax=ax, color='g')

plane_inter_1_2d = plane.point3d_to_2d(plane_inter_1[0])
plane_inter_2_2d = plane.point3d_to_2d(plane_inter_2[0])

ax2 = face.surface2d.plot()
plane_inter_1_2d.plot(ax=ax2, color='b')
plane_inter_2_2d.plot(ax=ax2, color='g')

assert surface2d.point_belongs(plane_inter_1_2d) == True
assert surface2d.point_belongs(plane_inter_2_2d) == False

p1_2dto3d = plane.point2d_to_3d(plane_inter_1_2d)
p1_2dto3d.plot(ax=ax, color='b')
assert p1_2dto3d.is_close(plane_inter_1[0])

face.babylonjs()
