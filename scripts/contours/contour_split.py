

import matplotlib.pyplot as plt

import design3d as d3d
from design3d.core import EdgeStyle
import design3d.primitives2d as p2d
from design3d import edges, curves
from design3d.utils.common_operations import random_color
plt, (ax1, ax2, ax3) = plt.subplots(1, 3)

u = d3d.Vector2D.random(0, 1, 0, 1)
u = u.unit_vector()
v = u.normal_vector()

l = 0.05

p1 = (v * l).to_point()
p2 = (p1 + l*u).to_point()
p3 = (p2 - 2*l*v).to_point()
p4 = (p3 + l*u).to_point()
p5 = (p4 + 2*l*u + 3*l*v).to_point()
p6 = (p5 + l*u).to_point()
p7 = (p6 - 4*l*v + l*v).to_point()
p8 = (p7 - l*u).to_point()
p9 = (0.5*(p5 + p6) - l*v).to_point()
p10 = (p4 - l*v).to_point()
p11 = (p1 - 3*l*v).to_point()

contour =p2d.ClosedRoundedLineSegments2D(
    [p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11],
    {3:0.3*l})

ax = contour.plot(ax=ax1)
line = curves.Line2D(d3d.O2D, u)
line2 = curves.Line2D(0.3*v, u+0.3*v)

line.plot(ax=ax1, edge_style=EdgeStyle(color='b'))
line2.plot(ax=ax1, edge_style=EdgeStyle(color='g'))

split_contours1 = contour.cut_by_line(line)
for c in split_contours1:
    c.plot(ax=ax2, edge_style=EdgeStyle(color=random_color()))
ax2.set_title('{} splitted contours'.format(len(split_contours1)))

split_contours2 = contour.cut_by_line(line2)
for c in split_contours2:
    c.plot(ax=ax3, edge_style=EdgeStyle(color='g'))
ax3.set_title('{} splitted contours'.format(len(split_contours2)))
