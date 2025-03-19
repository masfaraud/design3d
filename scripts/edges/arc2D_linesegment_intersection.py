import matplotlib.pyplot as plt

import design3d
import design3d.edges


i = design3d.Point2D(-0.2, -0.25)
e = design3d.Point2D(-1, 2)
s = design3d.Point2D(1.5, 2)

print('i', i)
print('s', s)
print('e', e)

a = design3d.edges.Arc2D.from_3_points(s, i, e)
start1 = design3d.Point2D(-2, -1.5)
end1 = design3d.Point2D(1.25, 1.75)
start2 = design3d.Point2D(1, 0)
end2 = design3d.Point2D(2, -2)
start3 = design3d.Point2D(0.7, 1.8)
end3 = design3d.Point2D(2, 2.2)
l1 = design3d.edges.LineSegment2D(start1, end1)
l2 = design3d.edges.LineSegment2D(start2, end2)
l3 = design3d.edges.LineSegment2D(start3, end3)


ax = a.plot()
l1.plot(ax=ax, color='r')
l2.plot(ax=ax, color='b')
l3.plot(ax=ax, color='g')
ax.set_xlim(-3, 3)
ax.set_ylim(-3, 3)


point1 = a.linesegment_intersections(l1)
point2 = a.linesegment_intersections(l2)
point3 = a.linesegment_intersections(l3)

assert len(point1) == 1
assert len(point2) == 1
assert len(point3) == 0
# l1 = design3d.edges.LineSegment2D

i = design3d.Point2D(-0.2, -0.25)
e = design3d.Point2D(1, 2)
s = design3d.Point2D(-1.5, -2)

a = design3d.edges.Arc2D.from_3_points(s, i, e)
start1 = design3d.Point2D(-2, -1.5)
end1 = design3d.Point2D(1.25, 1.75)
start2 = design3d.Point2D(1, 0)
end2 = design3d.Point2D(2, -2)
start3 = design3d.Point2D(0.7, 1.8)
end3 = design3d.Point2D(2, 2.2)
l1 = design3d.edges.LineSegment2D(start1, end1)
l2 = design3d.edges.LineSegment2D(start2, end2)
l3 = design3d.edges.LineSegment2D(start3, end3)


ax = a.plot()
l1.plot(ax=ax, color='r')
l2.plot(ax=ax, color='b')
l3.plot(ax=ax, color='g')
ax.set_xlim(-3, 3)
ax.set_ylim(-3, 3)


point1 = a.linesegment_intersections(l1)
point2 = a.linesegment_intersections(l2)
point3 = a.linesegment_intersections(l3)

assert len(point1) == 1
assert len(point2) == 0
assert len(point3) == 1
