import matplotlib.pyplot as plt
import numpy as np

import design3d
from design3d.core import EdgeStyle
import design3d.edges as d3de
import design3d.wires as d3dw
from design3d import curves


line_seg1 = d3de.LineSegment2D(design3d.Point2D(-0.5, -0.2), design3d.O2D)
line_seg2 = d3de.LineSegment2D(design3d.O2D, design3d.Point2D(0.3, 1))
line_seg3 = d3de.LineSegment2D(design3d.Point2D(0.3, 1), design3d.Point2D(1, 1))
line_seg4 = d3de.LineSegment2D(design3d.Point2D(1, 1), design3d.Point2D(1, -0.5))
line_seg5 = d3de.LineSegment2D(design3d.Point2D(1, -0.5), design3d.Point2D(-0.5, -0.2))

contour1 = d3dw.Contour2D([line_seg1, line_seg2, line_seg3, line_seg4, line_seg5])

line1 = curves.Line2D(design3d.Point2D(-0.5, 1), design3d.O2D)

cute_wire_line1 = contour1.cut_by_line(line1)
assert len(cute_wire_line1) == 2

line2 = curves.Line2D(design3d.Point2D(-0.5, -0.5), design3d.O2D)
cute_wire_line2 = contour1.cut_by_line(line2)
assert len(cute_wire_line2) == 2

line_segment1 = d3de.LineSegment2D(design3d.Point2D(1, -1), design3d.Point2D(2, 2))
line_segment2 = d3de.LineSegment2D(design3d.Point2D(2, 2), design3d.Point2D(-2, 1))
line_segment3 = d3de.LineSegment2D(design3d.Point2D(-2, 1), design3d.Point2D(-2, 0.7))
lie_segment4 = d3de.LineSegment2D(design3d.Point2D(-2, 0.7), design3d.Point2D(-1, 1))
points2d = [design3d.Point2D(-1, 1),
            design3d.Point2D(2, 2),
            design3d.Point2D(-2, -2),
            design3d.Point2D(1, -1)]
bspline = d3de.BSplineCurve2D(3, points2d, knot_multiplicities=[4, 4], knots=[0.0, 1.0])
bspline_middle_point = bspline.point_at_abscissa(bspline.length()*0.5)
bspline_tangent = bspline.tangent(0.5)
infinit_line1 = curves.Line2D(bspline_middle_point, bspline_tangent)
infinit_line2 = curves.Line2D(bspline.point_at_abscissa(bspline.length()*0.73), design3d.Point2D(-0.8, 1))
infinit_line3 = curves.Line2D(bspline_middle_point, design3d.Point2D(2, 2))

contour2 = d3dw.Contour2D([bspline, line_segment1, line_segment2, line_segment3, lie_segment4])

cut_contour_by_line1 = contour2.cut_by_line(infinit_line1)
assert len(cut_contour_by_line1) == 2


cut_contour_by_line2 = contour2.cut_by_line(infinit_line2)
assert len(cut_contour_by_line2) == 3

cut_contour_by_line3 = contour2.cut_by_line(infinit_line3)
assert len(cut_contour_by_line3) == 2

list_contours = [contour1, contour2, contour2, contour2]
lines = [line2, infinit_line1, infinit_line2, infinit_line3]
lists_cutted_contours = [cute_wire_line2, cut_contour_by_line1,
                         cut_contour_by_line2, cut_contour_by_line3]
fig, axs = plt.subplots(4, 3)
for i in range(0, 4):
    list_contours[i].plot(ax=axs[i][0])
    for j in range(0, 3):
        lines[i].plot(ax=axs[i][j], edge_style=EdgeStyle(color='r'))
        if j != 0:
            r, g, b = np.random.random(), np.random.random(), np.random.random()
            lists_cutted_contours[i][j-1].plot(ax=axs[i][j], edge_style=EdgeStyle(color=(r, g, b)))
