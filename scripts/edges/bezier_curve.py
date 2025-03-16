import matplotlib.pyplot as plt

import design3d as d3d
import design3d.edges as d3de

degree = 3
points = [d3d.Point2D(0, 0),
          d3d.Point2D(1, 1),
          d3d.Point2D(2, 0),
          d3d.Point2D(3, 0)]
bezier_curve2d = d3de.BezierCurve2D(degree=degree,
                                   control_points=points,
                                   name='bezier curve 1')
_, ax = plt.subplots()
bezier_curve2d.plot(ax=ax)
[p.plot(ax=ax) for p in points]

degree = 3
points = [d3d.Point3D(0, 0, 0),
          d3d.Point3D(1, 1, 2),
          d3d.Point3D(2, 1, 1),
          d3d.Point3D(3, 0, 4)]
bezier_curve3d = d3de.BezierCurve3D(degree=degree,
                                   control_points=points,
                                   name='bezier curve 1')
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')
bezier_curve3d.plot(ax=ax)
[p.plot(ax=ax) for p in points]
